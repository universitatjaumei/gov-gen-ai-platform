"""
Deploy: cloud
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.api.deps import get_session, get_current_user
from server.app.core.auth import UserInfo, create_token
from server.app.core.auth.models import UserRole
from server.app.core.config import get_settings
from server.app.core.rate_limit import limitar_login
from server.app.core.security import hash_password, verify_password
from server.app.database.models import SuperAdminAccount, AdminAccount

router = APIRouter(prefix="/auth", tags=["auth"])

# SEC.1: hash contra el que comparar cuando la cuenta no existe o no tiene contraseña, para
# que el tiempo de respuesta no delate cuáles de los correos probados son administradores.
# Se calcula una vez al importar; corresponde a una contraseña que nadie puede escribir.
_HASH_SENUELO = hash_password(uuid.uuid4().hex)


class LoginRequest(BaseModel):
    email: str
    password: str


class SetPasswordRequest(BaseModel):
    password: str = PydanticField(min_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"



async def _orgs_del_admin(session, partner_id: str) -> tuple[str, ...]:
    """Organizaciones que gestiona este Admin (SEC.2).

    Se resuelve al emitir el token y no en cada petición: el claim tiene que viajar dentro
    del JWT para que el servidor sepa de quién es el que pregunta sin volver a la BD en cada
    endpoint. El precio es que un alta de organización no se ve hasta el siguiente login,
    que para una relación admin↔organización —que cambia muy de tarde en tarde— sale a
    cuenta frente a una consulta por petición.
    """
    from server.app.modules.agents_hub.database.config_models import HubOrganizacion

    filas = await session.exec(
        select(HubOrganizacion.id).where(HubOrganizacion.partner_id == partner_id)
    )
    return tuple(str(fila) for fila in filas.all())


@router.post("/superadmin/login", response_model=TokenResponse)
async def login_superadmin(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un SuperAdminAccount con email + contraseña."""
    # SEC.4: por IP, porque en el login todavía no se sabe quién llama y esa es justamente
    # la gracia del ataque. Va lo primero: comprobar la contraseña de una cuenta que ya ha
    # gastado su cupo sería hacerle el trabajo al que prueba diccionarios.
    limitar_login(request)
    result = await session.exec(
        select(SuperAdminAccount).where(SuperAdminAccount.email == body.email.lower())
    )
    superadmin = result.first()

    if (
        not superadmin
        or not superadmin.is_active
        or not verify_password(body.password, superadmin.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # El superadmin va con la lista VACIA a proposito: en su rol eso es el comodin
    # «todas las organizaciones». Ver `core/auth/tenancy.py`.
    user_info = UserInfo(
        user_id=str(superadmin.admin_id),
        email=superadmin.email,
        role=UserRole.SUPERADMIN.value,
    )
    return TokenResponse(access_token=create_token(user_info))


@router.post("/admin/login", response_model=TokenResponse)
async def login_admin(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para un AdminAccount con email + contraseña (SEC.1, hallazgo A1).

    Hasta SEC.1 esto emitía el token comprobando solo que el email existiera: cualquiera que
    conociera un correo de administrador entraba con la contraseña que quisiera.

    **Una cuenta sin hash no entra.** El backfill de la migración deja NULL, y NULL es «login
    local deshabilitado» —SSO, PAT, o que un superadmin le fije contraseña—, jamás «pasa sin
    comprobar».

    **El error es el mismo en los tres casos** —cuenta inexistente, sin hash y contraseña
    incorrecta— y se paga siempre el coste de un `verify_password`: distinguirlos convertiría
    el formulario de login en un oráculo para enumerar administradores, y responder antes
    cuando el email no existe lo convierte en el mismo oráculo medido con un cronómetro.
    """
    # SEC.4: lo primero, antes incluso de mirar la cuenta. El hash de descarte de SEC.1
    # protege del oráculo temporal, pero nada impedía probar diccionarios a ritmo de red.
    limitar_login(request)

    result = await session.exec(
        select(AdminAccount).where(AdminAccount.email == body.email.lower())
    )
    # `one_or_none()` y no `first()` (USR.5): con el índice único de `adminaccount.email` son
    # equivalentes, y esto deja de compilar la suposición de que puede haber varias. Si algún
    # día vuelven a poder —porque alguien quite el índice—, esto levanta en vez de entrar con
    # una fila indeterminada, que es el 401 intermitente que el índice viene a cerrar.
    admin = result.one_or_none()

    hash_almacenado = getattr(admin, "hashed_password", None) if admin else None
    # Hash de descarte: sin esto, una cuenta inexistente responde sin hacer bcrypt y el
    # tiempo de respuesta delata qué correos son de administrador.
    contrasena_valida = verify_password(body.password, hash_almacenado or _HASH_SENUELO)

    if not admin or not admin.is_active or not hash_almacenado or not contrasena_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = UserInfo(
        user_id=admin.partner_id,
        email=admin.email,
        role=UserRole.ADMIN.value,
        organizacion_ids=await _orgs_del_admin(session, admin.partner_id),
    )
    return TokenResponse(access_token=create_token(user_info))


@router.post("/user/login", response_model=TokenResponse, operation_id="loginUsuario")
async def login_usuario(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Emite un JWT para una persona de `hub_users` con correo + contraseña (USR.2).

    **Existe porque el IdP institucional no está configurado y eso no tiene fecha**: los
    probadores del piloto tienen que poder entrar como ellos mismos en vez de compartir una
    credencial de administración. Es provisional por definición, y `LOCAL_USER_LOGIN_ENABLED`
    es lo que lo hace provisional de verdad: con `false` esta ruta responde **404**, como si no
    existiera, en vez de 403 —que confirmaría que está ahí, apagada—.

    **Las tres defensas son las de los otros dos logins, y están aquí por escrito porque
    escribirlas de memoria es cómo se repite la curva** que costó SEC.1 y SEC.4:

    1. `limitar_login` **lo primero**, antes de mirar la cuenta: comprobar la contraseña de una
       cuenta que ya gastó su cupo es hacerle el trabajo a quien prueba diccionarios.
    2. `verify_password` **siempre**, contra el hash guardado o contra `_HASH_SENUELO`. Sin eso
       el caso «no existe» responde sin pagar bcrypt y el cronómetro delata qué correos están
       dados de alta.
    3. **El mismo 401** —mismo `detail`, mismas cabeceras— en los cuatro casos: no existe, sin
       hash, inactiva y contraseña incorrecta. Un 403 para la inactiva diría que el correo
       existe, así que también es 401.

    **`hashed_password` NULL es «login local deshabilitado»**, jamás «pasa sin comprobar»: es el
    hallazgo A1 y se cierra aquí igual que en `login_admin`.

    **Y una persona no es un administrador.** El token lleva su rol real (`user`/`informer`) y
    su organización, con los grupos de SAML vacíos como el resto de logins locales: los grupos
    se leen de cada aserción, así que en una entrada local no hay ninguno que declarar. Con eso,
    no pasa los guardas de superadmin ni de admin, y sin organización no abre ningún chatbot de
    organización — que es lo que responde `tenancy.puede_acceder` de un no-superadmin.
    """
    if not get_settings().local_user_login_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    limitar_login(request)

    from server.app.modules.agents_hub.database.config_models import HubUser

    result = await session.exec(
        select(HubUser).where(HubUser.email == body.email.lower())
    )
    persona = result.first()

    hash_almacenado = getattr(persona, "hashed_password", None) if persona else None
    contrasena_valida = verify_password(body.password, hash_almacenado or _HASH_SENUELO)

    if not persona or not persona.is_active or not hash_almacenado or not contrasena_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # **Los datos del token se leen ANTES del commit, y no es estilo: es lo que hace que esto
    # funcione.** `commit()` expira los atributos de la instancia, así que leer `persona.id`
    # después dispara una recarga perezosa —IO síncrona— fuera del greenlet de SQLAlchemy, y eso
    # es un `MissingGreenlet` que llega al navegador como **500**. Pasó de verdad: lo destapó la
    # verificación de USR.4, y los tests de USR.2 no lo veían porque doblan la sesión.
    #
    # `login_admin` no tiene el problema porque no commitea; éste sí, porque anota la entrada.
    user_info = UserInfo(
        user_id=str(persona.id),
        email=persona.email,
        role=persona.role,
        organizacion_ids=(str(persona.organizacion_id),) if persona.organizacion_id else (),
    )

    # La columna existe desde AUTH.2 y hasta ahora sólo la escribía el ACS. La pantalla de
    # personas la usa para decidir si una fila se puede borrar (REV.8), así que una entrada por
    # esta vía tiene que contar igual que una por SSO.
    persona.last_login_at = datetime.now(timezone.utc)
    session.add(persona)
    await session.commit()

    return TokenResponse(access_token=create_token(user_info))


@router.patch(
    "/admins/{partner_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="setAdminPassword",
)
async def set_admin_password(
    partner_id: str,
    body: SetPasswordRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Fija o restablece la contraseña de un Admin. **Solo superadmin** (SEC.1).

    Es la contrapartida obligatoria de que el backfill deje los hashes en NULL: sin esta vía,
    las cuentas que ya existían se quedarían sin forma de entrar y el arreglo de A1 sería una
    puerta cerrada con la llave dentro.

    No lo puede hacer un admin, ni siquiera sobre su propia cuenta: cambiar la contraseña
    propia exige conocer la anterior, y ese flujo no es este prompt.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un superadministrador puede fijar la contraseña de un Admin",
        )

    admin = await session.get(AdminAccount, partner_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    admin.hashed_password = hash_password(body.password)
    session.add(admin)
    await session.commit()


@router.get("/me", response_model=dict)
async def get_me(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """La información del usuario autenticado, **con los módulos que tiene concedidos**.

    INF.7 — el menú y las rutas del frontend se generan iterando `modulos`. Antes no había nada
    que iterar: `App.tsx` metía todas las rutas bajo un `PrivateRoute` que solo comprobaba que
    hubiera sesión, así que cualquier cuenta veía chatbots, curación, informes y la
    configuración de LLM. El servidor decide y el cliente pinta lo que reciba.

    Y **quién manda sobre el rol** en este despliegue (IDE.1). Va aquí, en el sitio que ya
    responde «qué necesita saber esta sesión», y no en una pantalla concreta: la pantalla de
    personas tiene que avisar de que con la autoridad en el IdP editar un rol a mano es tirar
    el trabajo, y para avisar necesita el dato del servidor. No es un secreto: es configuración
    operativa, y adivinarla en el cliente sería inventarla.
    """
    from server.app.core.auth.modulos_service import modulos_del_usuario

    return {
        **current_user.to_dict(),
        "modulos": await modulos_del_usuario(session, current_user),
        "identity_role_authority": get_settings().identity_role_authority,
    }
