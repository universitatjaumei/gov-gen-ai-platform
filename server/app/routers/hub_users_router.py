"""Las personas de la plataforma: alta manual, edición y desactivación (IDE.3).

Deploy: cloud
Módulo: plataforma

Hasta aquí una persona solo existía si entraba por SSO, y entraba con el rol que resolviera la
aserción —por defecto `user`—. Promocionar a alguien exigía un `UPDATE` a mano en Postgres, que
es lo que no se le puede pedir a otra administración que despliegue esto: quien administra no
tiene por qué tener acceso a la base de datos, y no debería tenerlo.

**El alta no crea una credencial.** Crea la identidad y sus permisos; quien entra, entra por
SSO. Por eso `UsuarioCreate` **rechaza** un campo de contraseña en vez de ignorarlo: aceptado en
silencio haría creer que se guardó algo que no existe.

**El correo es la clave del reencuentro con el IdP**, así que se normaliza —sin espacios, en
minúsculas— al guardar y al buscar, y **no se puede editar**. Cambiarlo desde el panel
desengancharía a la persona de su identidad sin que se note hasta que intente entrar.

**Partido, no reservado (USR.9).** Crear personas, cambiar roles y borrar siguen siendo sólo de
superadministrador, y la razón es la de siempre: un admin que pudiera crear personas con rol
podría crearse un admin —la misma por la que `create_theme` reserva el tema de plataforma—.
**Listar y fijar la contraseña, en cambio, los puede hacer quien administra la organización de
esa persona**, acotado por tenencia. USR.1 ya había abierto la contraseña con ese argumento; el
listado se quedó cerrado, y sin él la capacidad existía por API y no por pantalla: para usarla
había que saberse el UUID de la persona.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo, UserRole
from server.app.core.auth.tenancy import (
    assert_org_access,
    puede_acceder,
    scope_query_to_orgs,
)
from server.app.core.security import hash_password
from server.app.modules.agents_hub.database.config_models import HubModuleGrant, HubUser
from server.app.modules.agents_hub.database.connection import get_async_session

router = APIRouter(prefix="/hub/users", tags=["hub-users"])

_require_superadmin = require_role(UserRole.SUPERADMIN.value)
#: Fijar la contraseña de una persona lo puede hacer también quien administra su organización
#: (USR.1). Ver `set_usuario_password` para por qué esta puerta es más ancha que las otras.
_require_admin = require_role(UserRole.SUPERADMIN.value, UserRole.ADMIN.value)

_ROLES = tuple(r.value for r in UserRole)


# AIS.3 — la definición se fue a `core/identidad.py`. Vivía aquí y la importaba el ACS de SAML,
# o sea `core/` dependiendo de un router. Se re-exporta porque es el nombre que usa el resto de
# este fichero; quien la necesite fuera, la trae de `core`.
from server.app.core.identidad import normalizar_correo  # noqa: E402

# USR.1 — **el mismo contrato de contraseña, no un segundo con el mismo mínimo escrito otra
# vez**: dos validaciones que hoy dicen `min_length=12` acabarían diciendo cosas distintas, y la
# que se relajara sería la débil. Si USR.7 necesita un tercero, entonces es el momento de
# sacarlo a `core/`; con dos, un import entre routers del mismo `Deploy: cloud` es más honesto
# que una capa nueva para un modelo de un campo.
from server.app.routers.auth_router import SetPasswordRequest  # noqa: E402


# ============================================
# Contrato
# ============================================


class UsuarioRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    organizacion_id: uuid.UUID | None
    is_active: bool
    origen: str
    created_at: datetime
    created_by: str | None
    last_login_at: datetime | None
    # Si esta fila se puede borrar, y por qué no. Lo decide el servidor (REV.8): el frontend no
    # calcula qué acciones están permitidas.
    puede_borrarse: bool = False
    motivo_no_borrable: str | None = None
    #: Si **quien pregunta** puede fijarle la contraseña de login local (USR.3). Misma regla
    #: maestra que `puede_borrarse`: la decide el servidor y el panel pinta el botón iterando
    #: la respuesta. Un `if (rol === 'superadmin')` en React sería la autorización escrita por
    #: segunda vez, y el día que un admin pueda gestionar su organización dirían cosas
    #: distintas.
    #:
    #: Falso en las cuentas de arranque de `superadminaccount`: viven en otra tabla y su
    #: contraseña no se toca desde esta pantalla.
    puede_fijar_contrasena: bool = False


class CapacidadesDePersonas(BaseModel):
    """Qué puede hacer **quien pregunta** en esta pantalla (USR.9).

    Regla maestra 2: la pantalla itera sobre `acciones_permitidas` y no las calcula. Las de fila
    —borrar, fijar contraseña— ya viajan en `UsuarioRead`; éstas son las de pantalla, que no
    tienen fila donde colgarse: si «crear» se decidiera en React con un `rol === 'superadmin'`,
    sería la autorización escrita por segunda vez y el día que cambie dirían cosas distintas.
    """

    acciones_permitidas: list[str]


class UsuarioCreate(BaseModel):
    """`extra="forbid"` a propósito: es lo que convierte «no hay contraseña» en un error
    legible en vez de un campo que se traga y se pierde."""

    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = None
    role: str = UserRole.USER.value
    organizacion_id: uuid.UUID | None = None
    is_active: bool = True

    model_config = {"extra": "forbid"}

    @field_validator("email")
    @classmethod
    def _correo_normalizado(cls, valor: str) -> str:
        limpio = normalizar_correo(valor)
        if "@" not in limpio:
            raise ValueError("el correo tiene que llevar @")
        return limpio

    @field_validator("role")
    @classmethod
    def _rol_conocido(cls, valor: str) -> str:
        if valor not in _ROLES:
            raise ValueError(f"rol desconocido. Admitidos: {', '.join(_ROLES)}")
        return valor


class UsuarioUpdate(BaseModel):
    """Sin `email`: es la clave del reencuentro con el IdP y cambiarlo desengancha a la
    persona de su identidad. `extra="forbid"` lo convierte en un 422 y no en un cambio
    silenciosamente ignorado."""

    display_name: str | None = None
    role: str | None = None
    organizacion_id: uuid.UUID | None = None
    is_active: bool | None = None

    model_config = {"extra": "forbid"}

    @field_validator("role")
    @classmethod
    def _rol_conocido(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in _ROLES:
            raise ValueError(f"rol desconocido. Admitidos: {', '.join(_ROLES)}")
        return valor


#: `origen` de las filas que vienen de `superadminaccount` y no de `hub_users` (REV.8).
ORIGEN_SUPERADMIN_DE_ARRANQUE = "superadmin"

MOTIVO_YA_ENTRO = (
    "Esta persona ya ha entrado, así que tiene rastro en interacciones, informes y "
    "revisiones. Desactívala en su lugar: borrarla dejaría ese rastro sin dueño."
)
MOTIVO_OTRA_TABLA = (
    "Es la cuenta de superadministración creada al instalar y vive en otra tabla; se "
    "gestiona desde el servidor, no desde esta pantalla."
)
MOTIVO_ULTIMO_SUPERADMIN = (
    "Es el único superadministrador activo que queda. Sin él nadie podría administrar la "
    "plataforma, y no habría forma de arreglarlo desde la propia aplicación."
)


def _a_lectura(
    fila: HubUser,
    *,
    motivo_no_borrable: str | None = None,
    quien: UserInfo | None = None,
) -> UsuarioRead:
    """El DTO de una persona, **con qué puede hacer con ella quien pregunta**.

    Lo decide el servidor y no la pantalla: es la regla de `AGENTS.md` —el frontend no calcula
    qué acciones están permitidas—. Si el React hiciera «si `last_login_at` es nulo, enseña el
    botón», esa regla viviría en dos sitios y un día dirían cosas distintas.

    `quien` es opcional para no obligar a los llamadores que sólo describen la fila; sin él,
    `puede_fijar_contrasena` es **falso**, que es el fallo seguro: una acción que no se ofrece
    se puede añadir, una que se ofrece y no autoriza es un 403 delante del usuario.
    """
    motivo = motivo_no_borrable or (MOTIVO_YA_ENTRO if fila.last_login_at else None)
    return UsuarioRead(
        id=fila.id,
        email=fila.email,
        display_name=fila.display_name,
        role=fila.role,
        organizacion_id=fila.organizacion_id,
        is_active=fila.is_active,
        origen=fila.origen,
        created_at=fila.created_at,
        created_by=fila.created_by,
        last_login_at=fila.last_login_at,
        puede_borrarse=motivo is None,
        motivo_no_borrable=motivo,
        # La misma función que autoriza el endpoint, no una copia de su regla.
        puede_fijar_contrasena=(
            puede_acceder(quien, fila.organizacion_id) if quien is not None else False
        ),
    )


async def _superadmins_de_arranque(session: AsyncSession) -> list[UsuarioRead]:
    """Las cuentas de `superadminaccount`, en solo lectura (REV.8).

    El listado leía sólo `hub_users`, así que **el superadministrador principal no aparecía en
    ninguna parte**: es la única cuenta real de una instalación recién creada y desde el panel
    no había forma de saber que existía.

    Se muestran, no se unifican: son cuatro tablas de identidad sin unificar y juntarlas es una
    migración de otro tamaño (IDE.2 hizo una parte). Van marcadas con su propio `origen` y sin
    poder borrarse, porque enseñarlas como una fila más haría creer que se editan desde aquí.

    El identificador es un uuid5 derivado del correo —`admin_id` es un entero y el contrato
    declara UUID—, el mismo normalizador que usan las concesiones por la misma razón.
    """
    from server.app.database.models import SuperAdminAccount
    from server.app.routers.redaccion._actor import user_to_uuid

    filas = (
        await session.execute(select(SuperAdminAccount).order_by(SuperAdminAccount.email))
    ).scalars().all()
    return [
        UsuarioRead(
            id=user_to_uuid(cuenta.email),
            email=cuenta.email,
            display_name=cuenta.name,
            role=UserRole.SUPERADMIN.value,
            organizacion_id=None,
            is_active=cuenta.is_active,
            origen=ORIGEN_SUPERADMIN_DE_ARRANQUE,
            created_at=cuenta.created_at,
            created_by=None,
            last_login_at=None,
            puede_borrarse=False,
            motivo_no_borrable=MOTIVO_OTRA_TABLA,
        )
        for cuenta in filas
    ]


async def _otro_superadmin_activo(session: AsyncSession, excluido: uuid.UUID) -> bool:
    """Si queda algún superadministrador activo **aparte** del que se va a tocar.

    Cuenta las dos tablas: si sólo mirara `hub_users`, la cuenta de arranque no valdría y la
    regla bloquearía una desactivación perfectamente segura.
    """
    from server.app.database.models import SuperAdminAccount

    otros = (
        await session.execute(
            select(HubUser).where(
                HubUser.role == UserRole.SUPERADMIN.value,
                HubUser.is_active.is_(True),
                HubUser.id != excluido,
            )
        )
    ).scalars().first()
    if otros is not None:
        return True

    de_arranque = (
        await session.execute(
            select(SuperAdminAccount).where(SuperAdminAccount.is_active.is_(True))
        )
    ).scalars().first()
    return de_arranque is not None


# ============================================
# Endpoints
# ============================================


@router.get(
    "/capacidades",
    response_model=CapacidadesDePersonas,
    operation_id="capacidadesDePersonas",
)
async def capacidades_de_personas(
    user: UserInfo = Depends(_require_admin),
) -> CapacidadesDePersonas:
    """Qué puede hacer quien pregunta en la pantalla de personas (USR.9).

    Va **antes** de `list_users` en el fichero por costumbre de orden, no por precedencia: no hay
    `GET /hub/users/{id}` con el que pudiera chocar la ruta.

    Un `user` a secas recibe 403 y no una lista vacía: quien no administra nada no tiene por qué
    saber que esta pantalla existe, y una lista vacía es una respuesta afirmativa a la pregunta
    «¿hay algo aquí?».
    """
    acciones = ["listar", "fijar_contrasena"]
    if user.role == UserRole.SUPERADMIN.value:
        # El mismo reparto que las puertas de los endpoints, leído del mismo sitio: crear,
        # editar y borrar son `_require_superadmin`.
        acciones += ["crear", "editar", "borrar"]
    return CapacidadesDePersonas(acciones_permitidas=acciones)


@router.get("", response_model=list[UsuarioRead])
async def list_users(
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> list[UsuarioRead]:
    """Quién existe en esta plataforma —o en tu organización, si es lo que administras.

    **REV.8 — incluye las cuentas de `superadminaccount`**, en solo lectura. Antes el listado
    leía sólo `hub_users` y el superadministrador principal no aparecía en ninguna parte, que es
    la única cuenta real de una instalación recién creada.

    **USR.9 — abierto a quien administra una organización, acotado por tenencia.** La acotación
    la hace `scope_query_to_orgs` y no un `if` aquí, para que la regla siga viviendo en un solo
    sitio; un principal con la lista de organizaciones vacía recibe `IN ()`, o sea nada, que es
    la diferencia entre «no ve nada» y «no se filtra». Las cuentas de arranque **no** se le
    enseñan: no son de ninguna organización, así que colarlas en un listado acotado sería
    filtrarle las cuentas de la plataforma por la puerta de atrás.

    Siguen sin listarse `AdminAccount` y `ClientAccount`, que tampoco están unificadas. La
    pantalla lo dice, para que nadie lea el listado como «todas las cuentas».
    """
    consulta = scope_query_to_orgs(select(HubUser), user, HubUser).order_by(HubUser.email)
    filas = (await session.execute(consulta)).scalars().all()
    personas = [_a_lectura(f, quien=user) for f in filas]
    if user.role != UserRole.SUPERADMIN.value:
        return personas
    return await _superadmins_de_arranque(session) + personas


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UsuarioCreate,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioRead:
    """Da de alta a una persona con su rol, **antes** de que entre por primera vez.

    Ese es el punto: cuando entre, el ACS encuentra esta fila por correo en vez de crear una
    nueva con el rol por defecto. Con `IDENTITY_ROLE_AUTHORITY=app` (IDE.1) el rol que se pone
    aquí sobrevive a todos los inicios de sesión posteriores.
    """
    existente = (
        await session.execute(select(HubUser).where(HubUser.email == body.email))
    ).scalars().first()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya hay una persona con el correo {body.email}",
        )

    fila = HubUser(
        id=uuid.uuid4(),
        email=body.email,
        display_name=body.display_name,
        role=body.role,
        organizacion_id=body.organizacion_id,
        is_active=body.is_active,
        origen="manual",
        created_by=user.user_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return _a_lectura(fila, quien=user)


@router.patch("/{user_id}", response_model=UsuarioRead)
async def update_user(
    user_id: uuid.UUID,
    body: UsuarioUpdate,
    user: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioRead:
    """Cambia rol, nombre, organización o actividad. **Desactivar es la baja** para quien ya usó
    la plataforma; a quien nunca entró se le puede borrar (ver `delete_user`).

    Una persona que ya entró tiene rastro en interacciones, informes y concesiones; borrarla
    dejaría ese rastro sin dueño. `is_active = false` cierra la puerta, que es lo que se quiere.

    **REV.8 — y no se puede dejar la plataforma sin superadministración**: desactivar al último
    que queda activo la deja sin nadie que administre y sin forma de arreglarlo desde la propia
    aplicación. Se comprueba también al cambiar el rol, porque bajar de rol al único que hay
    llega al mismo sitio por otra puerta.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    cambios = body.model_dump(exclude_unset=True)

    deja_de_administrar = fila.role == UserRole.SUPERADMIN.value and (
        cambios.get("is_active") is False
        or (cambios.get("role") is not None and cambios["role"] != UserRole.SUPERADMIN.value)
    )
    if deja_de_administrar and not await _otro_superadmin_activo(session, fila.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_ULTIMO_SUPERADMIN
        )

    for campo, valor in cambios.items():
        setattr(fila, campo, valor)

    await session.commit()
    await session.refresh(fila)
    return _a_lectura(fila, quien=user)


@router.patch(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="setUsuarioPassword",
)
async def set_usuario_password(
    user_id: uuid.UUID,
    body: SetPasswordRequest,
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Fija o restablece la contraseña de login local de una persona (USR.1).

    **Su gemelo `setAdminPassword` es sólo superadmin y éste no, a propósito**: quien da de alta
    a sus probadores es quien administra su organización, y obligar a que cada contraseña pase
    por el superadministrador convierte cada alta en un cuello de botella. La puerta se ensancha
    sólo hasta ahí: un admin puede fijarla a una persona **de una organización que gestione**, y
    quien no gestione ninguna no llega a nadie.

    **La acotación la resuelve `tenancy.py` y no un `if` de aquí.** Es la regla del módulo: el
    hallazgo A2 no fue que a un endpoint se le olvidara filtrar, fue que no había dónde. Una
    persona sin organización (nivel plataforma) sólo la alcanza un superadministrador, que es lo
    que `puede_acceder` responde cuando la organización es nula.

    **No devuelve nada** —204— y el hash no sale por ninguna otra respuesta: `UsuarioRead` se
    construye campo a campo y colarlo sería fácil, así que hay un test que lo vigila.

    Lo que este endpoint **no** hace es cambiar la contraseña propia conociendo la anterior: eso
    es USR.7, y es otro flujo porque exige comprobar la vieja para que una sesión robada no se
    quede la cuenta.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    assert_org_access(user, fila.organizacion_id)

    fila.hashed_password = hash_password(body.password)
    session.add(fila)
    await session.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    _: UserInfo = Depends(_require_superadmin),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Borra a una persona **que nunca ha entrado** (REV.8).

    IDE.4 decidió «desactivar, nunca borrar», y el razonamiento era bueno: quien ya entró tiene
    rastro en interacciones, informes y concesiones. Pero era absoluto de más — una fila creada
    a mano que nadie ha usado no tiene rastro de nada, y no había forma de quitarla, así que un
    correo mal escrito se quedaba en el listado para siempre.

    La regla es `last_login_at IS NULL`, que es exactamente «se creó a mano y no se ha usado»: si
    nunca entró, no pudo generar una interacción, un informe ni una revisión.

    **Sus concesiones se van con ella**, en la misma transacción: una concesión a alguien que ya
    no existe es una fila que ninguna pantalla enseña y que se queda ahí para siempre.
    """
    fila = await session.get(HubUser, user_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    if fila.last_login_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_YA_ENTRO)

    # El mismo agujero que vigila el `PATCH`, por la otra puerta.
    if fila.role == UserRole.SUPERADMIN.value and not await _otro_superadmin_activo(
        session, fila.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MOTIVO_ULTIMO_SUPERADMIN
        )

    concesiones = (
        await session.execute(
            select(HubModuleGrant).where(
                HubModuleGrant.subject_type == "usuario",
                HubModuleGrant.subject_id == str(fila.id),
            )
        )
    ).scalars().all()
    for concesion in concesiones:
        await session.delete(concesion)

    await session.delete(fila)
    await session.commit()
