"""
Servicio de gestión de licencias (Licenses) para Partners.

Permite administrar el estado de las suscripciones, ajustar cuotas de tokens 
y monitorizar la validez temporal de los derechos de uso de los clientes.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.models import License, ClientAccount, LicenseAuditLog
from automatia_shared.enums import LicenseStatus


class PartnerLicenseService:
    """
    Administrador de licencias vinculadas a los clientes de un Partner.

    Proporciona utilidades para la gestión económica y operativa de las licencias, 
    incluyendo un sistema de log de auditoría interna para cada cambio realizado.
    """

    def __init__(self, db_session: AsyncSession, partner_id: str):
        self.db = db_session
        self.partner_id = partner_id

    async def _get_license_if_owned(self, license_id: str) -> Optional[License]:
        """Obtener licencia solo si pertenece a un cliente del partner."""
        stmt = select(License).join(
            ClientAccount, License.client_id == ClientAccount.client_id
        ).where(
            License.license_id == license_id,
            ClientAccount.partner_id == self.partner_id
        )
        result = await self.db.exec(stmt)
        return result.first()

    async def list_licenses(self) -> List[License]:
        """Listar todas las licencias de clientes del partner."""
        stmt = select(License).join(
            ClientAccount, License.client_id == ClientAccount.client_id
        ).where(
            ClientAccount.partner_id == self.partner_id
        )
        result = await self.db.exec(stmt)
        return result.all()

    async def adjust_quota(self, license_id: str, add_tokens: int) -> Optional[License]:
        """
        Incrementa o ajusta la cuota de tokens disponibles en una licencia.
        
        Registra automáticamente la acción en el log de auditoría indicando 
        el valor previo y el nuevo valor.

        Args:
            license_id: Identificador de la licencia.
            add_tokens: Cantidad de tokens a sumar (o restar si es negativo).

        Returns:
            Optional[License]: La licencia actualizada o None si no pertenece al partner.
        """
        license = await self._get_license_if_owned(license_id)
        if not license:
            return None

        old_quota = license.quota_tokens
        license.quota_tokens += add_tokens

        self.db.add(license)
        await self._log_action(license_id, "QUOTA_INCREASED", {
            "old_quota": old_quota,
            "new_quota": license.quota_tokens,
            "added": add_tokens
        })
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def extend_validity(self, license_id: str, add_days: int) -> Optional[License]:
        """Extender fecha de validez."""
        license = await self._get_license_if_owned(license_id)
        if not license:
            return None

        old_date = license.valid_until
        license.valid_until = license.valid_until + timedelta(days=add_days)

        self.db.add(license)
        await self._log_action(license_id, "VALIDITY_EXTENDED", {
            "old_date": old_date.isoformat(),
            "new_date": license.valid_until.isoformat(),
            "days_added": add_days
        })
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def suspend_license(self, license_id: str, reason: str) -> Optional[License]:
        """
        Interrumpe el servicio de una licencia cambiando su estado a 'SUSPENDED'.
        
        Requiere un motivo que se guarda en el log de auditoría. Una licencia 
        suspendida no puede ser validada por el AIBrainService.

        Args:
            license_id: ID de la licencia a suspender.
            reason: Motivo de la suspensión (ej: 'Impago', 'Uso indebido').

        Returns:
            Optional[License]: La licencia en estado suspendido.
        """
        license = await self._get_license_if_owned(license_id)
        if not license:
            return None

        license.status = LicenseStatus.SUSPENDED.value

        self.db.add(license)
        await self._log_action(license_id, "SUSPENDED", {"reason": reason})
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def reactivate_license(self, license_id: str) -> Optional[License]:
        """Reactivar licencia suspendida."""
        license = await self._get_license_if_owned(license_id)
        if not license:
            return None

        # Check Client Status
        client = await self.db.get(ClientAccount, license.client_id)
        if not client or not client.is_active:
            raise ValueError("No se puede activar la licencia: El cliente está inactivo.")

        license.status = LicenseStatus.ACTIVE.value

        self.db.add(license)
        await self._log_action(license_id, "REACTIVATED", {})
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def get_expiring_soon(self, days: int = 15) -> List[License]:
        """Obtener licencias que expiran pronto."""
        cutoff = datetime.utcnow() + timedelta(days=days)

        stmt = select(License).join(
            ClientAccount, License.client_id == ClientAccount.client_id
        ).where(
            ClientAccount.partner_id == self.partner_id,
            License.valid_until <= cutoff,
            License.status == LicenseStatus.ACTIVE.value
        )
        result = await self.db.exec(stmt)
        return result.all()

    async def get_low_quota(self, threshold_percent: int = 20) -> List[License]:
        """Obtener licencias con quota baja."""
        licenses = await self.list_licenses()

        low_quota = []
        for lic in licenses:
            if lic.quota_tokens > 0:
                remaining_pct = (lic.remaining_tokens / lic.quota_tokens) * 100
                if remaining_pct < threshold_percent:
                    low_quota.append(lic)

        return low_quota

    async def _log_action(self, license_id: str, action: str, details: Dict[str, Any]):
        """
        Registra de forma persistente una acción administrativa sobre la licencia.

        Args:
            license_id: Licencia afectada.
            action: Código de la acción (ej: 'REACTIVATED').
            details: Diccionario con datos contextuales del cambio.
        """
        log = LicenseAuditLog(
            license_id=license_id,
            action=action,
            details=details,
            performed_by=self.partner_id,
            timestamp=datetime.utcnow()
        )
        self.db.add(log)

    async def get_license_audit(self, license_id: str) -> List[Dict[str, Any]]:
        """Obtener historial de cambios de una licencia."""
        stmt = select(LicenseAuditLog).where(
            LicenseAuditLog.license_id == license_id
        ).order_by(LicenseAuditLog.timestamp.desc())

        result = await self.db.exec(stmt)
        logs = result.all()

        return [
            {
                "action": log.action,
                "details": log.details,
                "performed_by": log.performed_by,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
