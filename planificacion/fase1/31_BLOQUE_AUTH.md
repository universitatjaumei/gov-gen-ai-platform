## Bloque AUTH — SSO SAML institucional + Personal Access Tokens (adelanto de Subfase 1.B.1, PENDIENTE)

> **Posición en orden de ejecución**: entre el Bloque 9Q (cerrado) y Fase 11 (Autoinstalación). Ver `PROJECT_STATE.md` → orden de ejecución acordado.

**Justificación del adelanto (2026-06-11)**: la autenticación SSO real (OIDC/SAML) estaba planificada como **Subfase 1.B.1** (`PLAN_DESARROLLO.md`, "antes Fase 5.1") y se difirió: en Fase 1 solo se ejecutó la identidad *visual* (Fase 10/temas). El Bloque MCP (siguiente) necesita un mecanismo de autenticación para **clientes máquina** antes de poder probarse. Se adelanta aquí la Subfase 1.B.1 completa para (a) cerrar el login institucional que la UJI exige por contrato y (b) habilitar la emisión de credenciales máquina que MCP consume.

**Distinción central (no confundir las dos piezas)**:

| Pieza | Para quién | Flujo | Bloque |
|---|---|---|---|
| **SSO SAML** | Humanos (admin/partner/usuario UJI) | Interactivo: redirect a IdP → aserción firmada → JWT de sesión | AUTH.1–AUTH.2, AUTH.4 |
| **PAT (Personal Access Token)** | Máquinas (servidor MCP headless) | No interactivo: token revocable de larga duración en cabecera `Authorization` | AUTH.3 |

Un servidor MCP **no puede** hacer el redirect-a-IdP de SAML. SAML autentica al humano que, ya logado, **emite un PAT** desde la UI; el PAT es lo que el cliente MCP usa. Por eso ambas piezas son necesarias y separadas.

**Decisiones de diseño tomadas (2026-06-11, vía `AskUserQuestion`)**:
- **Alcance**: SSO SAML + PAT completos (no solo PAT).
- **Enfoque SAML**: **Service Provider genérico SAML 2.0** testeable contra un **IdP de pruebas** (fixtures de aserción firmada / SimpleSAMLphp). La metadata real del IdP de la UJI se conecta por variable de entorno cuando esté disponible — **no bloquea** el desarrollo ni los tests.
- **Librería**: **`python3-saml`** (OneLogin) sobre xmlsec.

**Clasificación edge/cloud**:
- Login SAML y emisión/gestión de PAT son **`Deploy: cloud`** (autenticar humanos y emitir credenciales es trabajo del cloud/admin).
- La **validación** de credenciales (JWT y PAT) vive en `core/auth` (**compartido**): los routers edge la heredan vía `Depends`. En `DEPLOY_MODE=all` (dev) la búsqueda del PAT es local. La sincronización cloud→edge de la validación de PAT (cuando exista despliegue edge real) queda como **seguimiento documentado** vía `ConfigProvider`/sync API — no se implementa en este MVP.

**Reglas duras del bloque AUTH**:
- Ningún PAT se persiste en claro: se guarda solo `sha256(token)` + un `prefix` para identificarlo en la UI. El texto plano se devuelve **una sola vez** en la creación.
- La dependencia de auth acepta **JWT o PAT** de forma transparente, discriminando por prefijo (`pat_…`). Un PAT lleva *scopes*; un endpoint protegido por scope rechaza (403) un PAT sin el scope requerido.
- Solo `admin`/`partner` pueden emitir PAT. Los scopes de un PAT **nunca** exceden el rol del emisor.
- SAML con feature flag `SAML_ENABLED`: en dev, el login email+contraseña actual sigue disponible como fallback; en producción institucional se desactiva el fallback.

---

### Prompt AUTH.1 (RED/GREEN) — Service Provider SAML 2.0 con `python3-saml` + IdP de pruebas

**Modelo sugerido**: **Opus** — superficie de seguridad crítica (validación de firma/aserción), decisiones de diseño embebidas (mapa de atributos, adaptador request→python3-saml, fixtures de IdP de pruebas) y primer contacto con la librería.

**Objetivo**: implementar el SP SAML 2.0 que inicia el login contra el IdP institucional, consume la respuesta firmada (ACS) y publica la metadata del SP. Sin provisioning todavía (eso es AUTH.2): aquí se valida la aserción y se extraen NameID + atributos.

**Contexto**: auth actual = JWT de sesión email+contraseña (`server/app/routers/auth_router.py`, `Deploy: cloud`; `core/auth/jwt_handler.py`). `python3-saml` necesita un *dict* de request adaptado desde el `Request` de FastAPI (https on/off, http_host, script_name, get_data, post_data) y un *dict* de settings SP+IdP. El IdP de pruebas se materializa con un par de claves de test y fixtures de `SAMLResponse` firmadas (puede generarse con `xmlsec`/`python3-saml` en el propio test o con SimpleSAMLphp en docs; el test no debe depender de red).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.1 (RED/GREEN) — SP SAML 2.0 (python3-saml)

Deploy: cloud (router). Validación: compartida (core/auth).

## Dependencias
- Añadir `python3-saml` a pyproject.toml (arrastra `xmlsec` + `lxml`; documentar en
  README/DEV que requiere libxml2/libxmlsec1 del sistema — en Docker, paquetes apt).

## Settings (core/config.py)
SAML_ENABLED: bool = False
SAML_SP_ENTITY_ID, SAML_SP_ACS_URL, SAML_SP_SLS_URL
SAML_SP_X509_CERT, SAML_SP_PRIVATE_KEY (opcionales; para firmar AuthnRequest/metadata)
SAML_IDP_METADATA_URL | SAML_IDP_METADATA_XML  (una de las dos; XML inline para tests)
SAML_ATTR_EMAIL (default "urn:oid:0.9.2342.19200300.100.1.3" / "mail")
SAML_ATTR_NAME, SAML_ATTR_ROLE, SAML_ATTR_GROUPS (nombres de atributo en la aserción)
SAML_DEFAULT_ROLE: str = "user"
SAML_FRONTEND_RETURN_URL (a dónde redirige el ACS tras emitir el JWT)

## core/auth/saml/settings.py
- build_saml_settings() -> dict  # estructura sp/idp de python3-saml, a partir de env;
  si SAML_IDP_METADATA_URL, parsea metadata con OneLogin_Saml2_IdPMetadataParser
  (cacheable); si XML inline, idem desde string.
- InvalidSamlConfigError si falta config obligatoria con SAML_ENABLED=True.

## core/auth/saml/request_adapter.py
- async def prepare_saml_request(request: Request) -> dict
  # {"https", "http_host", "script_name", "get_data", "post_data"} desde el Request FastAPI.
  # Lee el body form (await request.form()) para post_data en el ACS.

## routers/saml_auth_router.py (prefix /auth/saml, Deploy: cloud)
- GET  /auth/saml/login        -> 302 al IdP (OneLogin_Saml2_Auth.login con RelayState opcional)
- POST /auth/saml/acs          -> procesa SAMLResponse: auth.process_response();
                                   si auth.get_errors() -> 401 SAML_VALIDATION_FAILED;
                                   si not auth.is_authenticated() -> 401;
                                   devuelve por ahora {nameid, attributes} (200) — el JWT llega en AUTH.2.
- GET  /auth/saml/metadata     -> XML de metadata del SP (content-type application/xml);
                                   400 si build_saml_settings produce errores de validación.
- GET  /auth/saml/logout (stub mínimo SLO: inicia SLS si SP_SLS_URL; si no, 501 documentado)
- Si SAML_ENABLED=False -> los endpoints responden 404/503 documentado (feature flag).
Registrar en _register_cloud (main.py) con docstring `Deploy: cloud`.

## Tests (mínimo 12) — tests/core/auth/test_saml_sp.py
- build_saml_settings construye sp/idp desde env (metadata XML inline de un IdP de pruebas).
- prepare_saml_request mapea https/host/post_data desde un Request simulado.
- GET /metadata devuelve XML bien formado con el EntityDescriptor del SP (entityID correcto).
- GET /login responde 302 con SAMLRequest en la query (Location al SSO del IdP de pruebas).
- POST /acs con SAMLResponse firmada válida (fixture) -> 200 con nameid + attributes esperados.
- POST /acs con firma manipulada -> 401 SAML_VALIDATION_FAILED (get_errors no vacío).
- POST /acs con aserción expirada / audience incorrecta -> 401.
- SAML_ENABLED=False -> endpoints 404/503; InvalidSamlConfigError si falta IdP con flag on.
Las fixtures de SAMLResponse firmada se generan en conftest con un cert/clave de test
(sin red): documentar el cómo. NUNCA usar el IdP real en tests.
```

**Verificación**: `uv run pytest tests/core/auth/` verde; `GET /auth/saml/metadata` produce XML válido; OpenAPI regenerado; `_register_cloud` incluye el router. Documentar en README la dependencia de sistema `libxmlsec1`.

---

### Prompt AUTH.2 (RED/GREEN) — Provisioning JIT + mapeo identidad SAML → cuenta + rol + JWT de sesión

**Modelo sugerido**: **Sonnet** — reglas de mapeo enumeradas y alcance cerrado; el SP ya valida la aserción en AUTH.1. (Opus solo si el mapeo multi-grupo→rol se complica.)

**Objetivo**: convertir una aserción SAML válida en una sesión del sistema: mapear NameID/atributos a un rol (`UserRole`), localizar o **aprovisionar (JIT)** la cuenta, emitir el JWT de sesión existente (`create_token`) y redirigir al frontend.

**Contexto**: cuentas actuales = `AdminAccount`, `PartnerAccount` (`server/app/database/models.py`). Los usuarios UJI que lleguen por SAML y no sean admin/partner necesitan una entidad propia. El JWT y la `UserInfo` (sub/email/role) ya existen y no cambian — SAML solo es un emisor adicional.

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.2 (RED/GREEN) — Provisioning JIT + JWT desde SAML

Deploy: cloud.

## ORM — HubSsoUser (HubConfigBase) en database/models.py
- id (UUID), email (único, lower), display_name, role (str, validado contra UserRole),
  external_id (NameID del IdP), idp_entity_id, created_at, last_login_at, is_active.
- Migración Alembic (aplicar al terminar; si la BD no responde, pedir arranque al usuario
  según CLAUDE.md).

## core/auth/saml/role_mapping.py
- SAML_GROUP_ROLE_MAP (env JSON: {"grupo-ldap": "partner", ...}) parseado a dict.
- resolve_role(attributes) -> str:
    1) si SAML_ATTR_ROLE presente y válido -> ese rol;
    2) si algún grupo de SAML_ATTR_GROUPS casa SAML_GROUP_ROLE_MAP -> rol mapeado
       (precedencia admin > partner > informer > user);
    3) si no -> SAML_DEFAULT_ROLE.

## core/auth/saml/identity_service.py
class SamlIdentityService(session):
  async def resolve_session(nameid, attributes) -> UserInfo:
    - email := attributes[SAML_ATTR_EMAIL][0] (obligatorio; si falta -> SamlMissingEmailError).
    - Si el email casa un AdminAccount activo -> UserInfo(role=admin).
    - Elif casa un PartnerAccount activo -> UserInfo(role=partner).
    - Else -> upsert HubSsoUser (rol vía resolve_role), actualizar last_login_at -> UserInfo.

## Integración en el ACS (routers/saml_auth_router.py)
- POST /auth/saml/acs (de AUTH.1) ahora: tras validar -> resolve_session -> create_token(user_info)
  -> 302 a SAML_FRONTEND_RETURN_URL con el token (querystring `#token=` o cookie httpOnly;
  decidir y documentar — preferir fragment/cookie sobre query para no filtrarlo en logs).

## Tests (mínimo 10) — tests/core/auth/test_saml_identity.py
- email de AdminAccount conocido -> UserInfo role=admin (sin crear HubSsoUser).
- email de PartnerAccount conocido -> role=partner.
- email desconocido + atributo de grupo mapeado a "partner" -> HubSsoUser role=partner (JIT).
- email desconocido sin grupo -> role=SAML_DEFAULT_ROLE.
- segundo login del mismo NameID -> no duplica HubSsoUser, actualiza last_login_at.
- aserción sin atributo email -> SamlMissingEmailError -> 401 en el ACS.
- resolve_role: precedencia admin>partner cuando hay varios grupos.
- ACS completo (fixture firmada) -> 302 a la return URL con token; decode_token del JWT -> UserInfo correcta.
```

**Verificación**: `uv run pytest tests/core/auth/` verde; migración aplicada (`alembic current` muestra la revisión); el ciclo login→ACS emite un JWT válido decodificable por `decode_token`.

---

### Prompt AUTH.3 (RED/GREEN) — Personal Access Tokens (PAT) revocables para clientes máquina

**Modelo sugerido**: **Opus** — toca la dependencia de auth que protege **todos** los requests (doble vía JWT/PAT) y maneja material criptográfico (hash de tokens, scopes); un error aquí es un agujero de seguridad.

**Objetivo**: emitir, validar y revocar tokens de acceso personal de larga duración con *scopes*, y extender la dependencia de autenticación para aceptarlos de forma transparente. Es el **prerrequisito real del Bloque MCP**.

**Contexto**: la dependencia actual es `get_current_user` (`server/app/api/deps.py`) que decodifica el Bearer JWT. Hay que admitir además PATs sin romper a los consumidores JWT existentes. `core/security.py` ya expone hashing (passlib) — reutilizar `sha256` para el token (no passlib: el token es de alta entropía, no una contraseña).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.3 (RED/GREEN) — PAT revocables + auth dual JWT/PAT

Deploy: emisión/gestión cloud; validación compartida (core/auth).

## ORM — HubPersonalAccessToken (HubConfigBase)
- id (UUID), owner_id (str), owner_role (str, validado UserRole), name (str),
  token_prefix (str, 8 chars visibles para identificar en UI), token_hash (sha256 hex),
  scopes (JSON list[str]), created_at, expires_at (nullable), last_used_at (nullable),
  revoked_at (nullable). Índice por token_prefix.
- Migración Alembic (aplicar al terminar).

## core/auth/pat/scopes.py
- Scopes válidos (constantes): "redaccion:templates:read", "redaccion:templates:write",
  "chatbots:read", "chatbots:write", "chat:test".
- UnknownScopeError si se pide un scope fuera del catálogo.

## core/auth/pat/service.py
class PatService(session):
  async def create(owner: UserInfo, name, scopes, expires_at?) -> tuple[HubPersonalAccessToken, str]
     - solo admin/partner (else PatForbiddenError); scopes ⊆ permitidos para el rol
       (un partner no puede emitir scopes que su rol no alcanza).
     - genera secret aleatorio (secrets.token_urlsafe(32)); token plano = f"pat_{prefix}_{secret}".
     - persiste token_prefix + sha256(token plano); DEVUELVE el plano UNA vez.
  async def verify(token: str) -> PatPrincipal   # UserInfo + scopes
     - localiza por prefix, compara sha256 en tiempo constante (hmac.compare_digest);
     - rechaza revocado/expirado (PatInvalidError); actualiza last_used_at.
  async def list_for(owner) -> list[...]   # SIN token plano ni hash
  async def revoke(owner, pat_id) -> None   # set revoked_at; 404 si no es del owner

## core/auth/dependencies (extender deps.py)
- get_current_user (o nuevo get_principal): si el Bearer empieza por "pat_" -> PatService.verify
  -> UserInfo con scopes adjuntos; si no -> flujo JWT actual (sin scopes -> scopes=None = "todos
  los de su rol vía sesión humana").
- require_scopes(*needed): dependency factory -> 403 PAT_SCOPE_MISSING si el principal es PAT y
  le falta algún scope. Un principal JWT humano no se filtra por scopes (sesión interactiva).

## routers/pat_router.py (prefix /auth/pats, Deploy: cloud)
- POST   /auth/pats        -> crea (body: name, scopes, expires_at?); 201 con el token plano
                              (único momento en que se ve); 403 si rol no admin/partner.
- GET    /auth/pats        -> lista metadatos del owner (prefix, name, scopes, fechas, revoked).
- DELETE /auth/pats/{id}   -> revoca; 404 si no es del owner.
Registrar en _register_cloud. operation_id explícito (Orval).

## Tests (mínimo 14) — tests/core/auth/test_pat.py + tests/test_pat_router.py
- create devuelve token plano "pat_..." y persiste solo prefix+sha256 (nunca el plano).
- verify(token válido) -> UserInfo+scopes; actualiza last_used_at.
- verify de token revocado -> PatInvalidError; expirado -> PatInvalidError.
- partner no puede crear PAT con scope fuera de su rol -> PatForbiddenError.
- usuario no admin/partner -> POST 403.
- list nunca expone hash ni plano; revoke de PAT ajeno -> 404.
- dependency: Bearer pat_... resuelve a UserInfo; require_scopes 403 si falta scope.
- dependency: Bearer JWT clásico sigue funcionando sin cambios (no regresión).
- comparación de hash en tiempo constante (compare_digest) — test de presencia.
```

**Verificación**: `uv run pytest tests/core/auth/ tests/test_pat_router.py` verde; migración aplicada; los tests de auth JWT preexistentes siguen verdes (sin regresión); OpenAPI regenerado.

---

### Prompt AUTH.4 (RED/GREEN) — Frontend: login SSO + gestión de PAT (UI) + pruebas manuales

**Modelo sugerido**: **Sonnet** — React + hooks Orval + i18n con patrones ya establecidos en el admin hub.

**Objetivo**: botón de login SSO institucional que redirige al SP y consume el token de retorno, y una pantalla de gestión de PAT (crear con scopes y caducidad, copiar el token una sola vez, revocar). Requiere **pruebas manuales** (navegador).

**Contexto**: login actual email+contraseña en el frontend (Prompt 9.3). Orval genera hooks desde `openapi.json` (endpoints de AUTH.3). i18n i18next (es/ca/en).

**Instrucciones al agente**:
```markdown
# PROMPT AUTH.4 (RED/GREEN) — UI login SSO + PAT

## Regenerar Orval
Hooks de PAT: useCreatePat / useListPats / useRevokePat. tsc --noEmit limpio.

## Login (frontend/src/admin/.../LoginPage)
- Botón "Entrar con SSO institucional" -> window.location = `${API}/auth/saml/login`
  (visible si VITE_SAML_ENABLED). Mantener email+contraseña como fallback (dev).
- Manejar el retorno del ACS: leer token del fragment/cookie, guardarlo en el auth context
  existente, redirigir a /hub. Si SAML_FRONTEND_RETURN_URL apunta a /auth/callback, crear
  esa ruta ligera que extrae el token y delega en el contexto.

## Gestión de PAT (frontend/src/admin/pages/AccessTokensPage.tsx, admin/partner)
- Tabla de PAT (name, prefix, scopes, creado, último uso, caducidad, revocar).
- "Crear token": modal react-hook-form+zod (name, multiselect de scopes, expiración opcional)
  -> useCreatePat -> mostrar el token plano UNA vez con botón "Copiar" y aviso
  "no volverás a verlo". Al cerrar, desaparece.
- Revocar -> useRevokePat con confirmación.
- Ruta /hub/access-tokens + entrada en la navegación de HubLayout.

## i18n (namespace `auth`, es/en/ca)
  Login SSO, fallback, etiquetas de scopes, mensajes del modal de creación,
  aviso de copia única, confirmación de revocado. NINGÚN string hardcodeado.

## Tests Vitest (mínimo 6)
- LoginPage muestra el botón SSO cuando VITE_SAML_ENABLED y redirige al /auth/saml/login.
- Callback extrae token del fragment y lo entrega al auth context (mock).
- AccessTokensPage: crear invoca useCreatePat y muestra el token plano una vez.
- Cerrar el modal oculta el token plano (no persiste en el DOM).
- Revocar invoca useRevokePat tras confirmación.
- a11y: expectNoA11yViolations sobre LoginPage y AccessTokensPage (helper de 20.1).

## Pruebas manuales (CLAUDE.md — requiere navegador)
Genera `pruebas_manuales_promptAUTH_4.bat` (ANSI 1252, sin BOM, vía PowerShell
[System.IO.File]::WriteAllText con Encoding 1252; primeros bytes @ech): arranque Docker,
migración, smoke `curl` a /auth/saml/metadata, y pasos UI: pulsar "Entrar con SSO"
(contra el IdP de pruebas si está configurado, o documentar que requiere metadata real),
crear un PAT con scopes redaccion:templates:read/write, copiarlo, revocarlo.
Casos límite: cerrar el modal sin copiar; revocar y comprobar que deja de autenticar.
Acompaña la respuesta con el bloque de instrucciones para el usuario (formato CLAUDE.md).
```

**Verificación**: `npm test` (Vitest) verde; `tsc --noEmit` limpio; `.bat` con bytes correctos; bloque de instrucciones manuales en la respuesta. **Cierra el Bloque AUTH.**

---
