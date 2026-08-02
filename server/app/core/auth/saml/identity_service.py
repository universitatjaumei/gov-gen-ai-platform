"""Provisioning de identidad desde una aserción SAML validada (AUTH.2). Deploy: cloud.

Mapea NameID + atributos a una sesión del sistema (``UserInfo``): localiza la cuenta
(SuperAdminAccount / AdminAccount) por email o aprovisiona (JIT) un ``HubSsoUser``.

**Qué se acepta de la aserción y qué no (SEC.2.1).** De la aserción salen la identidad y los
grupos: el email, el nombre y el atributo de grupos, que es lo que el IdP sabe y el backend
no. La **organización** no: esa sale de la configuración del despliegue
(``SAML_ORGANIZACION_ID``). La diferencia no es de estilo — si la organización viniera en un
atributo, quien controla el IdP podría declarar a qué organización pertenece cada persona que
entra, y con ella a qué corpus llega. Es la misma regla anti-escalada que
``delegated_actor.py`` aplica a la cabecera delegada.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from server.app.core.auth.models import UserInfo
from server.app.core.auth.saml.role_mapping import resolve_role
from server.app.core.config import get_settings
from server.app.database.models import SuperAdminAccount, AdminAccount
from server.app.modules.agents_hub.database.config_models import HubSsoUser


logger = logging.getLogger(__name__)


class SamlMissingEmailError(Exception):
    """La aserción no contiene el atributo de email requerido."""


def _first(attributes: dict, name: str) -> str | None:
    values = attributes.get(name) or []
    return values[0] if values else None


def _grupos(attributes: dict) -> tuple[str, ...]:
    """Grupos declarados por el IdP. Los consume el modo `restricted` de SEC.2.1."""
    settings = get_settings()
    return tuple(str(g) for g in (attributes.get(settings.saml_attr_groups) or ()))


def _organizacion_del_idp() -> uuid.UUID | None:
    """La organización del IdP, tomada de la **configuración** (SEC.2.1).

    Nunca de la aserción: un IdP institucional pertenece a una institución, y esa relación
    la fija quien despliega. Si viniera en un atributo, quien controla el IdP decidiría a
    qué organización pertenece cada persona que entra —y con ella, a qué corpus llega—.

    Sin configurar, se devuelve `None` y el usuario entra sin organización: fail-closed, la
    misma regla de SEC.2 según la cual un claim vacío no es un comodín.
    """
    bruto = get_settings().saml_organizacion_id
    if not bruto:
        return None
    try:
        return uuid.UUID(bruto)
    except ValueError:
        return None


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

        superadmin = (
            await self.session.execute(
                select(SuperAdminAccount).where(SuperAdminAccount.email == email)
            )
        ).scalars().first()
        grupos = _grupos(attributes)

        if superadmin and superadmin.is_active:
            # Sin organizaciones a propósito: en un superadmin el vacío es el comodín
            # «todas» (SEC.2), no «ninguna».
            return UserInfo(
                user_id=str(superadmin.admin_id),
                email=superadmin.email,
                role="superadmin",
                saml_groups=grupos,
            )

        admin = (
            await self.session.execute(
                select(AdminAccount).where(AdminAccount.email == email)
            )
        ).scalars().first()
        if admin and admin.is_active:
            # Las mismas organizaciones que el login local le daría: entrar por el IdP no
            # puede significar entrar con menos permisos de los que la cuenta ya tiene.
            return UserInfo(
                user_id=admin.partner_id,
                email=admin.email,
                role="admin",
                organizacion_ids=await self._orgs_del_admin(admin.partner_id),
                saml_groups=grupos,
            )

        return await self._provision_sso_user(nameid, attributes, email)

    async def _provision_sso_user(
        self, nameid: str, attributes: dict, email: str
    ) -> UserInfo:
        settings = get_settings()
        role = resolve_role(attributes)
        display_name = _first(attributes, settings.saml_attr_name) or email
        organizacion_id = await self._organizacion_configurada()
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
                organizacion_id=organizacion_id,
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
            # Se refresca en cada entrada: si el despliegue configura la organización
            # después de la primera visita, el usuario no tiene que esperar a que alguien
            # le toque la fila a mano. Y si se retira, deja de tener acceso.
            sso.organizacion_id = organizacion_id

        await self.session.commit()
        await self.session.refresh(sso)
        return UserInfo(
            user_id=str(sso.id),
            email=sso.email,
            role=sso.role,
            organizacion_ids=(str(sso.organizacion_id),) if sso.organizacion_id else (),
            saml_groups=_grupos(attributes),
        )

    async def _organizacion_configurada(self) -> "uuid.UUID | None":
        """La organización del IdP, comprobando que existe.

        Un id mal escrito en la configuración reventaría el ACS contra la clave ajena, y
        caerse en el login es peor que no dar acceso: se avisa por log y el usuario entra
        sin organización, que es el mismo fallo seguro que cuando no hay nada configurado.
        """
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        organizacion_id = _organizacion_del_idp()
        if organizacion_id is None:
            return None

        existe = (
            await self.session.execute(
                select(HubOrganizacion.id).where(HubOrganizacion.id == organizacion_id)
            )
        ).scalars().first()
        if existe is None:
            logger.warning(
                "SAML_ORGANIZACION_ID=%s no corresponde a ninguna organización: los "
                "usuarios de este IdP entrarán sin acceso a recursos de organización",
                organizacion_id,
            )
            return None
        return organizacion_id

    async def _orgs_del_admin(self, partner_id: str) -> tuple[str, ...]:
        """Las organizaciones del Admin, igual que en el login local (SEC.2)."""
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        filas = await self.session.execute(
            select(HubOrganizacion.id).where(HubOrganizacion.partner_id == partner_id)
        )
        return tuple(str(fila) for fila in filas.scalars().all())
