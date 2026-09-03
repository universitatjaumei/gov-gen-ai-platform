"""Provisioning de identidad desde una aserción SAML validada (AUTH.2). Deploy: cloud.

Mapea NameID + atributos a una sesión del sistema (``UserInfo``): localiza la cuenta
(SuperAdminAccount / AdminAccount) por email o aprovisiona (JIT) un ``HubUser``.

**Qué se acepta de la aserción y qué no (SEC.2.1).** De la aserción salen la identidad y los
grupos: el email, el nombre y el atributo de grupos, que es lo que el IdP sabe y el backend
no. La **organización** no: esa sale de la configuración del despliegue
(``SAML_ORGANIZACION_ID``). La diferencia no es de estilo — si la organización viniera en un
atributo, quien controla el IdP podría declarar a qué organización pertenece cada persona que
entra, y con ella a qué corpus llega. Es la misma regla anti-escalada que
``delegated_actor.py`` aplica a la cabecera delegada.

**Y el rol depende de quién sea la autoridad (IDE.1).** Con ``IDENTITY_ROLE_AUTHORITY=app``
—el defecto— el atributo de rol de la aserción no se lee: el rol lo pone una persona, y quien
llega nuevo entra con ``SAML_DEFAULT_ROLE``. Con ``idp`` se resuelve de la aserción en cada
entrada, que es lo que se hacía antes de IDE.1.

Ignorar el atributo también al **crear** la fila es deliberado: ``resolve_role`` acepta
``superadmin``, así que confiar en la aserción la primera vez deja que un IdP mal configurado
acuñe un superadministrador con la autoridad puesta en la aplicación — el interruptor
protegería solo lo ya creado, que es la mitad inútil del problema.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from server.app.core.auth.models import UserInfo
from server.app.core.auth.saml.role_mapping import resolve_role
from server.app.core.config import get_settings
from server.app.database.models import SuperAdminAccount, AdminAccount
from server.app.modules.agents_hub.database.config_models import HubUser


logger = logging.getLogger(__name__)


class SamlMissingEmailError(Exception):
    """La aserción no contiene el atributo de email requerido."""


class SamlUserInactiveError(Exception):
    """La persona existe y está desactivada (IDE.3).

    `is_active` existía desde AUTH.2 y **nadie la miraba**: desactivar a alguien lo quitaba del
    listado y lo dejaba entrando igual. Se distingue de «no existe» a propósito: quien
    administra necesita saber que la cuenta está, pero cerrada.
    """


def _first(attributes: dict, name: str) -> str | None:
    values = attributes.get(name) or []
    return values[0] if values else None


def _grupos(attributes: dict) -> tuple[str, ...]:
    """Grupos declarados por el IdP. Los consume el modo `restricted` de SEC.2.1."""
    settings = get_settings()
    return tuple(str(g) for g in (attributes.get(settings.saml_attr_groups) or ()))


def _rol_aprovisionado(attributes: dict, *, fila_existente: HubUser | None) -> str | None:
    """El rol con el que se crea o se refresca una fila, según quién sea la autoridad.

    Devuelve ``None`` cuando **no hay que tocar** el rol de una fila que ya existe: es la
    diferencia entre «pon este rol» y «deja el que haya», y colapsarlas en una sola cadena
    obligaría a que el llamante volviera a decidir.
    """
    settings = get_settings()

    if settings.identity_role_authority == "idp":
        return resolve_role(attributes)

    # Autoridad de la aplicación. El atributo de rol de la aserción no se lee ni al crear.
    declarado = _first(attributes, settings.saml_attr_role)
    if declarado:
        # Nadie sabe todavía qué atributos manda cada IdP —los configura quien lo administra—,
        # así que decirlo en el log convierte esa incógnita en un dato observable. En INFO y no
        # en WARNING: no es un fallo, es la configuración haciendo lo que se le pidió.
        logger.info(
            "El IdP declara role=%r y se ignora: IDENTITY_ROLE_AUTHORITY=app, "
            "así que el rol lo pone una persona. Cambia el ajuste a `idp` si quieres que "
            "manden los atributos de la aserción.",
            declarado,
        )

    if fila_existente is not None:
        return None
    return settings.saml_default_role


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
        # La misma normalización que usa el alta manual (IDE.3), importada de allí y no
        # reescrita: si las dos se separan, una persona dada de alta como `Fabra@UJI.es` deja
        # de ser la que llega del IdP como `fabra@uji.es`, y el alta se queda muerta.
        from server.app.core.identidad import normalizar_correo

        email = normalizar_correo(email)

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

        # `one_or_none()` por lo mismo que en `login_admin` (USR.5): `adminaccount.email` es
        # único, así que aquí no puede haber dos filas — y si alguna vez las hubiera, es mejor
        # levantar que reencontrar a quien entra con una cuenta indeterminada de las dos.
        admin = (
            await self.session.execute(
                select(AdminAccount).where(AdminAccount.email == email)
            )
        ).scalars().one_or_none()
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
        display_name = _first(attributes, settings.saml_attr_name) or email
        organizacion_id = await self._organizacion_configurada()
        now = datetime.now(timezone.utc)

        sso = (
            await self.session.execute(
                select(HubUser).where(HubUser.email == email)
            )
        ).scalars().first()

        # IDE.1 — el rol depende de quién sea la autoridad, y hay que saber si la fila ya
        # existía para distinguir «pon este rol» de «deja el que haya».
        rol = _rol_aprovisionado(attributes, fila_existente=sso)

        if sso is None:
            sso = HubUser(
                email=email,
                display_name=display_name,
                role=rol or settings.saml_default_role,
                external_id=nameid,
                idp_entity_id=settings.saml_idp_metadata_url or None,
                organizacion_id=organizacion_id,
                is_active=True,
                created_at=now,
                last_login_at=now,
            )
            self.session.add(sso)
        elif not sso.is_active:
            # Antes de tocar nada: una cuenta cerrada no se refresca ni deja pasar.
            raise SamlUserInactiveError(
                f"La cuenta {email} está desactivada en esta plataforma"
            )
        else:
            sso.display_name = display_name
            # `None` significa «no lo toques»: con la autoridad en la aplicación, el rol que
            # puso una persona tiene que sobrevivir al siguiente inicio de sesión. Que no lo
            # hiciera es el motivo por el que este bloque existe.
            if rol is not None:
                sso.role = rol
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
