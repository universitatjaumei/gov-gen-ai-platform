## Bloque USR — Contraseña local para las personas, hasta que llegue el SSO (PENDIENTE, planificado el 2026-09-01)

> **Posición en orden de ejecución**: puede ir en cualquier momento; no depende del Bloque
> Deploy ni de REG/DIN. Lo pide el piloto: los probadores de Gerencia y de la plataforma tienen
> que entrar antes de que el IdP de la UJI esté configurado, y eso no tiene fecha.

**Origen**: pregunta del usuario el 2026-09-01 — «hasta que no tengamos configurado el SSO puedo
habilitar usuarios con contraseñas o no está previsto?». La respuesta medida contra el código fue
que **no**: `hub_users` no tiene columna de contraseña, así que sus identidades solo pueden venir
del ACS de SAML. Login local hay únicamente para `SuperAdminAccount` y `AdminAccount`.

**Por qué NO se resuelve dando rol de administrador a los probadores**, que fue la primera idea:
`AdminAccount.partner_id` es la clave primaria, y el enlace con las organizaciones es
`HubOrganizacion.partner_id` (en la UJI, `uji`). Solo la fila cuyo `partner_id` sea exactamente
`uji` ve los asistentes de la UJI, así que cinco probadores serían cinco filas con cinco
`partner_id` y cuatro entrarían sin ver ninguna organización. Se degrada a **una credencial
compartida**: sin atribución por persona en `hub_interactions` —que es justo lo que necesita la
pantalla de revisión que pide Gerencia (Bloque RHR)—, con poderes de panel completos y sin poder
retirar el acceso a uno solo.

**Lo que ya existe y NO se rehace** (medido el 2026-09-01, no supuesto):
- `HubUser` / `hub_users` es un registro de personas completo, con `origen IN ('sso','manual')`,
  `created_by`, `role`, `organizacion_id`, `is_active` y `last_login_at`.
- **El alta manual ya está hecha (IDE.3)**: `POST /hub/users`, `PATCH /hub/users/{id}`,
  `DELETE /hub/users/{id}` y la pantalla `frontend/src/admin/pages/UsuariosPage.tsx` con sus tests.
- `assert_chatbot_access` ya resuelve el caso: un chatbot `authenticated` se abre a cualquier
  actor que pertenezca a su organización, y una persona tiene `organizacion_id`. No hay ningún
  chatbot `restricted` en producción, así que **no hace falta ningún grupo de SAML** todavía.

Es decir: **el bloque añade una columna, dos endpoints y una acción de panel**, no un subsistema
de identidad.

**Reglas duras del bloque USR**:
- **`hashed_password` NULL significa «login local deshabilitado»**, jamás «pasa sin comprobar».
  Es la misma semántica que `AdminAccount.hashed_password` y por el mismo motivo (SEC.1, hallazgo
  A1): la lectura contraria reabre el agujero por la puerta de atrás. Test propio.
- **El login nuevo se endurece igual que los dos que ya hay**, y no «parecido»: `limitar_login`
  **lo primero** (SEC.4), hash señuelo para que el tiempo de respuesta no delate qué correos
  existen, y **el mismo 401 en los tres casos** (cuenta inexistente, sin hash, contraseña mala).
  Copiar el endpoint sin copiar sus tres defensas es el modo de fallo previsible aquí.
- **Contraseña y SSO son ortogonales.** Una persona puede tener las dos vías; el ACS no toca
  `hashed_password` y fijar contraseña no cambia `origen`. `origen` dice **quién creó la fila**,
  no cómo entra.
- **Interruptor para apagarlo**, porque es provisional por definición:
  `LOCAL_USER_LOGIN_ENABLED` (defecto `true` ahora). Con `false`, `POST /auth/user/login`
  responde 404 y la acción desaparece del panel. Sin esto, «hasta que llegue el SSO» se
  convierte en «para siempre», que es como envejecen los apaños.
- **Una persona no es un administrador.** El JWT lleva su `role` real (`user` / `informer`) y su
  `organizacion_id`; `saml_groups` vacío, como en el resto de logins locales. Un probador no
  puede ver el panel de plataforma ni un chatbot de otra organización, y eso se verifica en
  navegador, no se supone.

---

### Prompt USR.1 (RED/GREEN) — La columna y la vía para fijar la contraseña

**Modelo sugerido**: **Sonnet** — alcance cerrado: una columna, una migración y un endpoint cuyo
gemelo (`setAdminPassword`) ya está escrito y sirve de plantilla.

**Objetivo**: `hub_users.hashed_password` (nullable) con migración aplicada, y
`PATCH /hub/users/{user_id}/password` para fijarla o restablecerla.

**Contexto**: el gemelo es `PATCH /auth/admins/{partner_id}/password` (`setAdminPassword`), que
es **solo superadmin** porque cambiar la propia exige conocer la anterior y ese flujo no existe.
Aquí hay una diferencia deliberada: un **admin** debe poder fijar la contraseña de una persona
**de su organización**, porque es quien da de alta a sus probadores y obligar a que pase por el
superadministrador convierte cada alta en un cuello de botella. La acotación por organización la
resuelve `core/auth/tenancy.py`, no una comprobación a mano en el endpoint.

**Instrucciones al agente**:
```markdown
# PROMPT USR.1 (RED/GREEN) — hashed_password en hub_users + fijar contraseña

## Modelo ORM (config_models.py, clase HubUser)
- hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
- Docstring de la columna: NULL = login local deshabilitado (SSO o nada), NUNCA «sin
  comprobar». Mismo criterio que AdminAccount.hashed_password.
- NO tocar el CheckConstraint de `origen`: la contraseña no es una procedencia.

## Migración
- Alembic autogenerate + revisión manual. Aplicar con `uv run alembic upgrade <rev>` y
  pegar `alembic current`. Comprobar el `downgrade`.
- hub_users es HubConfigBase (se sincroniza cloud→edge): comprobar que la sync API no
  arrastra el hash a ningún sitio donde no deba estar, y si lo arrastra, decirlo.

## Endpoint PATCH /hub/users/{user_id}/password (hub_users_router.py)
- operation_id explícito: setUsuarioPassword.
- Autorización: superadmin siempre; admin SOLO si la persona pertenece a una de sus
  organizaciones, resuelto con tenancy.py (no con un `if` propio).
- Cuerpo: {password: str} con la MISMA validación de longitud/fuerza que
  SetPasswordRequest de auth_router; reutilizar el contrato, no escribir otro.
- 404 si la persona no existe; 403 si el llamante no puede.
- Nada de devolver el hash ni la contraseña en la respuesta: 204.

## Tests (RED primero)
- Un admin de OTRA organización recibe 403.
- Un usuario con rol `user` recibe 403 aunque sea su propia fila.
- Tras fijarla, la fila tiene hash de 60 caracteres y NO es la contraseña en claro.
- El hash no viaja en ninguna respuesta de /hub/users (ni en el listado ni en el detalle):
  test que lo fija, porque UsuarioRead se construye a mano y es fácil colar el campo.
```

**Verificación**: los directorios tocados + `tests/infra/test_suite_hygiene.py`. Migración
aplicada con su `alembic current` pegado.

---

### Prompt USR.2 (RED/GREEN) — El login de la persona

**Modelo sugerido**: **Sonnet** — el endpoint tiene dos gemelos en el mismo fichero; lo que
importa es no perderse ninguna de sus tres defensas, y eso es una lista, no un diseño.

**Objetivo**: `POST /auth/user/login`, con el mismo endurecimiento que los dos existentes, que
emite un JWT con el rol real y la organización de la persona.

**Contexto**: la razón de que este prompt exista separado del USR.1 es que aquí está el riesgo.
El login de Admin nació **sin comprobar nada** (SEC.1, hallazgo A1) y el de superadmin tuvo que
aprender el hash señuelo y el rate limit por separado. Un tercer login escrito de memoria repite
esa curva. Se escribe leyendo `login_admin` al lado.

**Instrucciones al agente**:
```markdown
# PROMPT USR.2 (RED/GREEN) — POST /auth/user/login

## El endpoint (auth_router.py, junto a los otros dos)
- limitar_login(request) LO PRIMERO, antes de mirar la cuenta (SEC.4).
- select(HubUser).where(HubUser.email == body.email.lower())
- verify_password SIEMPRE, contra el hash almacenado o _HASH_SENUELO si no hay.
- 401 idéntico —mismo detail, mismas cabeceras— en los tres casos: no existe, sin hash,
  contraseña incorrecta.
- Rechazar también is_active=False con el MISMO 401 (no un 403: distinguirlo dice si el
  correo existe).
- Si LOCAL_USER_LOGIN_ENABLED es false: 404, como si la ruta no existiera.
- UserInfo(user_id=str(fila.id), email=fila.email, role=fila.role,
  organizacion_ids=(str(fila.organizacion_id),) if fila.organizacion_id else ()).
  saml_groups vacío, como el resto de logins locales.
- Actualizar last_login_at (la columna existe y hoy solo la escribe el ACS).

## Tests (RED primero)
- Persona con contraseña fijada: 200 y el JWT lleva su rol, NO `admin`.
- hashed_password NULL: 401 (el caso que reabriría A1).
- is_active=False: 401.
- organizacion_id NULL: entra, y con la lista vacía no abre ningún chatbot de
  organización — se comprueba llamando a assert_chatbot_access, no razonando.
- LOCAL_USER_LOGIN_ENABLED=false: 404.
- El tiempo de respuesta con correo inexistente y con correo existente y contraseña mala
  no se distingue por ausencia de bcrypt: test de que verify_password se llama en los dos
  casos (con espía, no con cronómetro, que es flaky).
- Un usuario `user` autenticado por esta vía NO pasa los Depends de superadmin ni de admin:
  un test por cada uno de los dos guardas, porque es el fallo que convertiría un probador
  en administrador.
```

**Verificación**: los directorios tocados + higiene. Contrato regenerado (la API cambia).

---

### Prompt USR.3 (RED/GREEN) — El panel: entrar y dar contraseña

**Modelo sugerido**: **Sonnet** — dos ficheros de frontend que ya existen con sus tests.

**Objetivo**: `LoginPage` prueba también el login de persona, y `UsuariosPage` gana la acción de
fijar contraseña. Sin strings a mano (i18next) y con los hooks generados por Orval.

**Contexto**: `LoginPage` ya prueba superadmin y luego admin en orden; este prompt añade el
tercero. **Con cuidado en el orden y en el mensaje**: encadenar tres 401 y enseñar «credencial
incorrecta» es exactamente lo que ocurrió el 2026-09-01, cuando el usuario no podía entrar y los
dos 401 de la cadena no distinguían «contraseña mala» de «esta cuenta no tiene login local».

**Instrucciones al agente**:
```markdown
# PROMPT USR.3 (RED/GREEN) — LoginPage y UsuariosPage

## LoginPage.tsx
- Tercer intento: superadmin -> admin -> user, en ese orden.
- El mensaje de error solo cambia si los TRES fallan. No filtrar cuál de los tres existía.
- Test: con el mock del tercero devolviendo 200, se navega al destino que corresponde al
  rol (una persona `user` no aterriza en el panel de plataforma).

## UsuariosPage.tsx
- Acción «Fijar contraseña» por fila, visible solo si el llamante puede (superadmin, o
  admin de esa organización). La decisión la trae el servidor si ya viaja en el DTO; si no
  viaja, este prompt la añade al DTO — NO se calcula en el cliente (regla maestra 2).
- Formulario con react-hook-form + zodResolver, validación alineada con el contrato.
- Toast de confirmación; el valor no se vuelve a mostrar.
- i18n en los cuatro idiomas que ya tenga el fichero de traducciones, sin excepción.

## Contrato
- Regenerar con Orval y usar los hooks generados, no fetch a mano.
```

**Verificación**: `npm test` de los ficheros tocados y `tsc --noEmit` limpio.

---

### Prompt USR.4 (verificación en navegador) — El recorrido de un probador, y lo que NO puede hacer

**Modelo sugerido**: **Sonnet** — es ejecución y observación; el criterio está escrito.

**Objetivo**: recorrer en el navegador el alta de una persona, su contraseña, su entrada y su
conversación con un chatbot `authenticated`, y **comprobar los límites**, que es la mitad del
valor de este prompt.

**Instrucciones al agente**:
```markdown
# PROMPT USR.4 — Verificación en navegador

## El recorrido bueno
1. Como superadmin, crear una persona en UsuariosPage con rol `user` y organización UJI.
2. Fijarle contraseña.
3. Cerrar sesión, entrar como esa persona.
4. Conversar con un chatbot `authenticated` de su organización y obtener respuesta.

## Los límites (cada uno con su evidencia: URL, texto y consola)
5. Esa persona NO ve la sección de plataforma.
6. NO puede abrir un chatbot de otra organización: 403 con code ACCESS_MODE_FORBIDDEN.
7. NO puede fijar la contraseña de nadie, ni la propia: 403.
8. Desactivarla (is_active=false) y comprobar que deja de entrar: 401.

## Y lo que hay que mirar aunque nadie lo pida
- read_console_messages y read_network_requests en cada paso: los 500 y los preflight
  rechazados no se ven en la pantalla.
- Que el hash no aparezca en NINGUNA respuesta del panel (mirar el JSON real en red, no
  el DOM).
```

**Verificación**: evidencia pegada en el informe de cierre. Si algo de los puntos 5-8 falla, se
arregla en este bloque con TDD (repro -> rojo -> arreglo -> suite), no se reporta y se deja.

---

### Prompt USR.5 (RED/GREEN) — El correo de administrador que no es único

**Modelo sugerido**: **Sonnet** — un índice, una migración y un test.

**Objetivo**: cerrar el defecto latente que salió al investigar este asunto:
`AdminAccount.email` **no tiene restricción de unicidad** mientras `login_admin` hace
`result.first()`.

**Contexto**: con dos filas del mismo correo, entrar dependería del orden que devuelva Postgres —
un 401 intermitente imposible de diagnosticar desde fuera, y el mismo patrón que se descartó en
`SuperAdminAccount` (que sí lo tiene único) el 2026-09-01. Hoy `adminaccount` está vacía en
producción, así que es el momento barato de arreglarlo: mañana hace falta una migración de datos.

**Instrucciones al agente**:
```markdown
# PROMPT USR.5 (RED/GREEN) — unicidad de AdminAccount.email

- Índice único sobre AdminAccount.email + migración; comprobar el downgrade.
- Antes de crearlo, la migración debe FALLAR con un mensaje claro si ya hay duplicados,
  en vez de romper con el error de Postgres: es una base ajena la que puede tenerlos.
- Comprobar si el mismo defecto está en ClientAccount.email y en HubUser.email (esta
  última ya es unique=True; verificarlo, no suponerlo).
- Test: insertar dos AdminAccount con el mismo correo levanta IntegrityError.
- De paso, `login_admin` pasa de `.first()` a `.one_or_none()`: con el índice único es
  equivalente, y deja de compilar la suposición de que puede haber varias.
```

**Verificación**: los directorios tocados + higiene; migración aplicada con `alembic current`.

---


---

### Prompt USR.6 (DISEÑO + RED/GREEN) — Alta manual de administradores, y varias personas por organización

**Modelo sugerido**: **Opus** — no es un endpoint más: hay una decisión de modelo de datos que
condiciona el resto, y la toma este prompt.

**Objetivo**: que se puedan crear cuentas de administración desde el panel y que **varias personas
administren la misma organización**, que hoy no se puede expresar.

**Contexto — el problema, medido el 2026-09-01**:
- **No hay ningún endpoint que cree un `AdminAccount`.** Solo lo hacen `seeds.py` y
  `bootstrap.py`, y `bootstrap` crea un superadministrador único que no pisa. Dar de alta a
  alguien exige un script contra la base de datos, que es como se dieron de alta las seis cuentas
  del piloto.
- **`AdminAccount.partner_id` es la clave primaria** y el enlace con las organizaciones es
  `HubOrganizacion.partner_id`, un `String(255)` indexado sin unicidad. La relación es
  *un partner → muchas organizaciones*, así que **una organización tiene exactamente un
  administrador posible**: el de su `partner_id`. Cuatro personas administrando la UJI no es
  representable, y crear cuatro filas produce cuatro cuentas que entran y abren el panel con la
  lista de asistentes vacía.
- Tampoco hay endpoint para crear ni para cambiar la contraseña de un **superadministrador**:
  `PATCH /auth/admins/{partner_id}/password` solo cubre administradores.

**La decisión que este prompt tiene que tomar** (y escribir en el PR, no solo en el código). Dos
caminos, y **no son equivalentes**:

- **(a) Tabla puente `admin_organizaciones`.** Conserva `AdminAccount` y añade la
  muchos-a-muchos. Barato y local, pero **consolida cuatro tablas de identidad** y deja la
  contraseña, el rol y la organización de una persona repartidos según por qué puerta entró.
- **(b) `HubUser` con `role='admin'` pasa a ser la identidad de administración real**, y
  `AdminAccount` se queda con lo que de verdad es suyo —el partner, los créditos, la facturación—
  dejando de ser una identidad de login. Es más trabajo, pero es la dirección que el propio
  docstring de `HubUser` ya señala: «sigue habiendo cuatro tablas de identidad […] unificarlas es
  una migración de datos con riesgo y merece bloque propio».

**Recomendación**: **(b)**, y no por elegancia. Con (a) el piloto acaba con dos clases de
administrador según la tabla en que se creó, y la pantalla de personas tendría que enseñar las
dos; y la deuda de las seis cuentas elevadas (ver `PROJECT_STATE.md`) se cierra sola con (b),
porque esas personas pasan a ser `HubUser` con su rol. Con (a) habría que hacer las dos cosas.
Si (b) no cabe en un bloque, se parte — pero se parte hacia (b), no se hace (a) «de momento».

**Instrucciones al agente**:
```markdown
# PROMPT USR.6 — Alta de administradores y varias personas por organización

## Primero: decidir y escribirlo
- Leer HubUser, AdminAccount, ClientAccount, SuperAdminAccount, tenancy.py y
  _orgs_del_admin, y escribir en docs/ la decisión (a) o (b) con su motivo y su
  camino de migración. Sin esto, el resto del prompt es código sin criterio.
- Contar qué hay en producción antes de decidir: si `adminaccount` sigue vacía, (b) no
  necesita migrar ninguna fila, y eso cambia el coste.

## Después, según la decisión
- El alta de cuentas de administración se hace por API + panel, NO por script.
- Reutilizar el contrato de contraseña que ya existe; no escribir un tercero.
- Si se toca el login: las tres defensas de SEC.1/SEC.4 se conservan, con test.
- La acotación por organización la resuelve tenancy.py, no un `if` en el endpoint.

## Y lo que NO se hace en este prompt
- No unificar ClientAccount ni la propiedad de los workspaces de redacción
  (`user_to_uuid`, SEC.8.1). Es la parte con riesgo real y merece su propio bloque.
```

**Verificación**: los directorios tocados + higiene; migración aplicada con `alembic current`;
recorrido en navegador de dos personas administrando la misma organización.

---

### Prompt USR.7 (RED/GREEN) — Cambiar la propia contraseña

**Modelo sugerido**: **Sonnet** — alcance cerrado; lo único a cuidar es no abrir un oráculo.

**Objetivo**: que una persona pueda cambiar su propia contraseña conociendo la anterior.

**Contexto**: hoy **no existe en ninguno de los roles**. Lo dice el docstring de
`set_admin_password`: «cambiar la contraseña propia exige conocer la anterior, y ese flujo no es
este prompt». La consecuencia se vio el 2026-09-01: las seis cuentas del piloto se crearon con la
misma contraseña y **ninguno de sus dueños puede cambiarla**, así que cualquiera de los seis puede
entrar como otro y la atribución de las valoraciones vale lo que valga ese secreto compartido.

**Instrucciones al agente**:
```markdown
# PROMPT USR.7 (RED/GREEN) — POST /auth/me/password

- Cuerpo: {password_actual, password_nueva}. Exige la actual SIEMPRE, también para un
  superadministrador: es lo que impide que una sesión robada se quede la cuenta.
- Sirve a las tres clases de identidad que tengan login local, resolviendo la tabla por
  el rol del JWT. Una sola ruta; tres endpoints serían tres sitios donde olvidarse algo.
- limitar_login (o su equivalente) también aquí: si no, es un oráculo para adivinar la
  contraseña actual a ritmo de red.
- 401 si la actual no casa; 204 si va bien. No devolver nada del hash.
- Test de que la contraseña vieja deja de servir y la nueva sirve, para las tres clases.
- Panel: formulario en el menú de la propia cuenta, i18n completo.
```

**Verificación**: los directorios tocados + higiene; contrato regenerado; cambio de contraseña
probado en navegador de punta a punta.

---

**Al cerrar el bloque**: suite completa (`uv run pytest tests` desde Git Bash) y frontend
(`--no-file-parallelism`); contrato regenerado; migraciones aplicadas con su `alembic current`;
`pruebas_manuales/pruebas_manuales_bloqueUSR.bat` **solo** con lo que el agente no puede
verificar él mismo — que aquí es poco, porque el recorrido entero es navegable: previsiblemente
nada más que dar de alta a los probadores reales de Gerencia con sus correos y decidir sus roles.

---
