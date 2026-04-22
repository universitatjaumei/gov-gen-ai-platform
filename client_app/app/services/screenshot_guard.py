
"""
Screenshot Guard Service.

Middleware de seguridad que intercepta y valida capturas de pantalla
antes de enviarlas al Brain (LLM multimodal).
"""
import json
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import SecurityPolicy, ConnectionLog
from automatia_shared.enums import ScreenshotPolicyEnum


class ScreenshotGuardAction(str, Enum):
    """Acción resultante de la evaluación de política."""
    ALLOW = "ALLOW"              # Enviar sin confirmación
    REQUIRE_REVIEW = "REQUIRE_REVIEW"  # Mostrar al usuario para aprobar
    BLOCK = "BLOCK"              # Bloquear envío


class ScreenshotGuard:
    """
    Servicio de seguridad encargado de validar las capturas de pantalla antes de su procesamiento.

    Evalúa la política de seguridad activa (SecurityPolicy) para decidir si una captura
    es segura para enviar al motor de IA, requiere aprobación explícita del usuario
    o debe ser bloqueada inmediatamente.
    """

    async def check_policy(self, url: str) -> ScreenshotGuardAction:
        """
        Evalúa la política para una URL dada.

        Args:
            url: URL de la página capturada

        Returns:
            ScreenshotGuardAction indicando qué hacer
        """
        policy = await self._get_active_policy()

        # Sin política = default seguro
        if policy is None:
            await self._log_decision(url, ScreenshotGuardAction.REQUIRE_REVIEW, "no_policy")
            return ScreenshotGuardAction.REQUIRE_REVIEW

        policy_type = policy.screenshot_policy

        # BLOCK: siempre bloquear
        if policy_type == ScreenshotPolicyEnum.BLOCK.value:
            await self._log_decision(url, ScreenshotGuardAction.BLOCK, "policy_block")
            return ScreenshotGuardAction.BLOCK

        # TRUSTED: permitir si dominio en whitelist
        if policy_type == ScreenshotPolicyEnum.TRUSTED.value:
            if self._is_trusted_domain(url, policy):
                await self._log_decision(url, ScreenshotGuardAction.ALLOW, "trusted_domain")
                return ScreenshotGuardAction.ALLOW
            # Dominio no trusted -> cae a REVIEW

        # REVIEW (default) o TRUSTED con dominio no whitelisted
        await self._log_decision(url, ScreenshotGuardAction.REQUIRE_REVIEW, "review_required")
        return ScreenshotGuardAction.REQUIRE_REVIEW

    async def _get_active_policy(self) -> Optional[SecurityPolicy]:
        """
        Recupera la política de seguridad marcada como activa en la base de datos local.

        Returns:
            Objeto SecurityPolicy si existe uno activo, None en caso contrario.
        """
        async with AsyncSession(client_engine) as session:
            statement = select(SecurityPolicy).where(SecurityPolicy.is_active == True)
            result = await session.exec(statement)
            return result.first()

    def _is_trusted_domain(self, url: str, policy: SecurityPolicy) -> bool:
        """
        Verifica si el dominio de la URL proporcionada forma parte de la lista blanca de confianza.

        Args:
            url: URL completa de la captura.
            policy: Instancia de la política de seguridad actual.

        Returns:
            True si el dominio es de confianza, False de lo contrario.
        """
        try:
            domain = self._extract_domain(url)
            trusted_domains = json.loads(policy.trusted_screenshot_domains)

            # Match exacto o subdominio
            for trusted in trusted_domains:
                if domain == trusted or domain.endswith(f".{trusted}"):
                    return True
            return False
        except Exception:
            return False

    def _extract_domain(self, url: str) -> str:
        """
        Extrae y normaliza el dominio base de una URL (p.ej., 'google.com' de 'https://www.google.com/search').

        Args:
            url: Cadena con la URL a analizar.

        Returns:
            Dominio normalizado en minúsculas.
        """
        try:
            parsed = urlparse(url)
            host = parsed.netloc or parsed.path

            # Quitar www. si existe
            if host.startswith("www."):
                host = host[4:]

            # Quitar puerto si existe
            if ":" in host:
                host = host.split(":")[0]

            return host.lower()
        except Exception:
            return ""

    async def _log_decision(self, url: str, action: ScreenshotGuardAction, reason: str):
        """
        Registra la decisión tomada por el guardia en el log de auditoría.

        Args:
            url: URL afectada.
            action: Acción aplicada (ALLOW, BLOCK, etc.).
            reason: Motivo técnico de la decisión.
        """
        try:
            domain = self._extract_domain(url)
            async with AsyncSession(client_engine) as session:
                log = ConnectionLog(
                    connection_type="screenshot_guard",
                    connection_name=domain or "unknown",
                    event_type="policy_check",
                    status="info",
                    message=f"Screenshot policy: {action.value}",
                    details=json.dumps({
                        "url": url[:200],  # Truncar URLs largas
                        "action": action.value,
                        "reason": reason
                    })
                )
                session.add(log)
                await session.commit()
        except Exception:
            pass  # No fallar por logging


# === Singleton Instance ===
screenshot_guard = ScreenshotGuard()
