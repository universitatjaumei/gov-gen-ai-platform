"""Provisioning de identidad desde una aserción SAML validada (AUTH.2).

Mapea NameID + atributos a una sesión del sistema (``UserInfo``): localiza la cuenta
(AdminAccount / PartnerAccount) por email o aprovisiona (JIT) un ``HubSsoUser``.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from server.app.core.auth.models import UserInfo
from server.app.core.auth.saml.role_mapping import resolve_role
from server.app.core.config import get_settings
from server.app.database.models import AdminAccount, PartnerAccount
from server.app.modules.agents_hub.database.config_models import HubSsoUser


class SamlMissingEmailError(Exception):
    """La aserción no contiene el atributo de email requerido."""


def _first(attributes: dict, name: str) -> str | None:
    values = attributes.get(name) or []
    return values[0] if values else None


class SamlIdentityService:
    """Resuelve una aserción SAML en una ``UserInfo`` del sistema."""

    def __init__(self, session) -> None:
        self.session = session

    async def resolve_session(self, nameid: str, attributes: dict) -> UserInfo:
        settings = get_settings()

        email = _first(attributes, settings.saml_attr_email)
        if not email:
            raise SamlMissingEmailError(
                f"SAML assertion missing email attribute '{settings.saml_attr_email}'"
            )
        email = email.lower()

        admin = (
            await self.session.execute(
                select(AdminAccount).where(AdminAccount.email == email)
            )
        ).scalars().first()
        if admin and admin.is_active:
            return UserInfo(
                user_id=str(admin.admin_id), email=admin.email, role="admin"
            )

        partner = (
            await self.session.execute(
                select(PartnerAccount).where(PartnerAccount.email == email)
            )
        ).scalars().first()
        if partner and partner.is_active:
            return UserInfo(
                user_id=partner.partner_id, email=partner.email, role="partner"
            )

        return await self._provision_sso_user(nameid, attributes, email)

    async def _provision_sso_user(
        self, nameid: str, attributes: dict, email: str
    ) -> UserInfo:
        settings = get_settings()
        role = resolve_role(attributes)
        display_name = _first(attributes, settings.saml_attr_name) or email
        now = datetime.now(timezone.utc)

        sso = (
            await self.session.execute(
                select(HubSsoUser).where(HubSsoUser.email == email)
            )
        ).scalars().first()

        if sso is None:
            sso = HubSsoUser(
                email=email,
                display_name=display_name,
                role=role,
                external_id=nameid,
                idp_entity_id=settings.saml_idp_metadata_url or None,
                is_active=True,
                created_at=now,
                last_login_at=now,
            )
            self.session.add(sso)
        else:
            sso.display_name = display_name
            sso.role = role
            sso.external_id = nameid
            sso.last_login_at = now

        await self.session.commit()
        await self.session.refresh(sso)
        return UserInfo(user_id=str(sso.id), email=sso.email, role=sso.role)
