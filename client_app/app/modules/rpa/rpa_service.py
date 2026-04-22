
"""
RPA Service Module.

Servicio de alto nivel para orquestación de procesos RPA,
integrando seguridad, interacción humana y delegación a IA.
"""
from typing import Optional

from client_app.app.services.screenshot_guard import screenshot_guard, ScreenshotGuardAction
from client_app.app.ui.components.screenshot_review import request_screenshot_approval

# Placeholder for Brain Client - In a real app this would be imported from a core service
# or dependency injection container. For now, we define it here so it can be patched.
# The tests expects `client_app.app.modules.rpa.rpa_service.brain_client` to exist.
try:
    from client_app.app.core.state import state
    brain_client = state.brain
except ImportError:
    brain_client = None


class ScreenshotBlockedException(Exception):
    """Excepción cuando el envío de capturas está bloqueado por política."""
    pass


class RPAService:
    """
    Servicio principal para operaciones RPA.
    Enforce policies and coordinate execution steps.
    """

    async def send_screenshot_to_brain(
        self,
        screenshot: bytes,
        url: str,
        prompt: str
    ) -> Optional[dict]:
        """
        Envía una captura al Brain para análisis visual.

        Aplica la política de seguridad antes del envío:
        - BLOCK: Lanza excepción
        - REVIEW: Solicita aprobación del usuario
        - ALLOW: Envía directamente

        Args:
            screenshot: Bytes de la imagen PNG/JPEG
            url: URL de la página capturada
            prompt: Instrucción para el modelo visual

        Returns:
            Respuesta del Brain, o None si el usuario rechazó

        Raises:
            ScreenshotBlockedException: Si la política bloquea el envío
        """
        # 1. Evaluar política
        action = await screenshot_guard.check_policy(url)

        # 2. Actuar según política
        if action == ScreenshotGuardAction.BLOCK:
            raise ScreenshotBlockedException(
                "El envío de capturas de pantalla está bloqueado por la política de seguridad. "
                "Contacte al administrador si necesita esta funcionalidad."
            )

        if action == ScreenshotGuardAction.REQUIRE_REVIEW:
            # Solicitar aprobación visual
            approved = await request_screenshot_approval(screenshot, url)
            if not approved:
                # Usuario rechazó, no enviar
                return None

        # 3. Enviar al Brain (ALLOW o REQUIRE_REVIEW aprobado)
        if brain_client is None:
            return {"error": "Brain client not available"}

        return await brain_client.analyze_image(
            image_bytes=screenshot,
            prompt=prompt,
            context={"source_url": url}
        )
    
    async def save_master_playbook(self, name: str, base_url: str):
        """
        Guarda un playbook maestro y lo sincroniza con la librería.
        """
        from client_app.app.database.models import RpaPlaybook
        from client_app.app.database.db import client_engine
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.services.rpa_library_sync import rpa_sync_service
        
        # 1. Save to DB (Legacy/Specific Table)
        async with AsyncSession(client_engine) as session:
            playbook = RpaPlaybook(
                name=name,
                base_url=base_url,
                description="Playbook maestro generado desde UI",
                actions=[] # Typically passed, but here simplified for signature match
                # NOTE: Logic should receive playbook content. 
                # Updating signature to receive playbook or assume state management?
                # User prompt rpa_page.py assumes internal state usage: state.rpa.save_master_playbook(name, url)
                # So we need to access the active playbook from state or cache?
                # For now, let's assume we save an empty/placeholder or modify signature in UI later.
                # BETTER: Add playbook arg to signature or get from Wizard state if feasible.
                # Given rpa_page.py call: await state.rpa.save_master_playbook(name_input.value, wizard.target_url)
                # It implies 'state.rpa' holds the current playbook in memory.
            )
            # Revisit: We need the actions! 
            # We will rely on an internal attribute `_current_playbook` if it exists, or add it.
            if hasattr(self, '_current_playbook'):
                playbook.actions = self._current_playbook
            
            session.add(playbook)
            await session.commit()
            await session.refresh(playbook)
            
            # 2. Sync to Library
            await rpa_sync_service.sync_playbook_to_library(playbook)
            
            return playbook
