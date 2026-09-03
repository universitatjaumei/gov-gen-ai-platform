## Bloque IDE — Identidad y permisos: alta manual hoy, grupos del IdP mañana

> **Planificado el 2026-08-22**, al preguntar el usuario dónde estaba prevista la gestión de usuarios
> y los permisos a módulos. La respuesta corta era «en ningún sitio»: `grep` sobre `planificacion/` no
> encuentra nada en Fase 1, 2 ni 3. La respuesta larga es más interesante, porque **medio mecanismo ya
> está construido**.
>
> **Lo que el usuario quiere, dicho por él**: «de momento me gustaría que se pudieran dar usuarios con
> roles manualmente y que el SSO se utilizara para identificar a los usuarios, pero en el futuro
> debería poder vincularse también el SSO a un atributo que permitiera esta asignación de permisos
> desde el ERP de origen y no desde la aplicación».
>
> **Lo que ya existe, medido:**
>
> | Pieza | Estado |
> |---|---|
> | El rol **ya sale de la aserción SAML** | `role_mapping.resolve_role`: atributo de rol explícito → mapeo grupo→rol con precedencia por privilegio → rol por defecto. Configurable con `SAML_ATTR_ROLE`, `SAML_GROUP_ROLE_MAP`, `SAML_DEFAULT_ROLE` |
> | Los grupos del IdP **viajan enteros** | `_grupos(attributes)` → `UserInfo.saml_groups` → claim `groups` del JWT → `EffectiveActor.saml_groups` |
> | Y **ya tienen un consumidor en producción** | el modo `restricted` de un chatbot cruza `allowed_saml_groups` con los grupos del actor (`assert_chatbot_access`) |
> | `HubSsoUser` **ya es** una tabla de usuarios | correo único, `display_name`, `role`, `organizacion_id`, `is_active`, `last_login_at`. Lo que le falta no es forma: es un escritor que no sea SAML |
>
> **Los dos huecos exactos:**
>
> 1. **El rol se sobreescribe en cada login.** `identity_service._provision_sso_user` hace
>    `sso.role = role` sin condición en la rama del usuario existente. Por eso hoy no se pueden «dar
>    usuarios con roles manualmente»: pones el rol y el siguiente inicio de sesión lo pisa. No falta
>    la pantalla; es que la pantalla no serviría.
> 2. **Los módulos no se conceden por grupo.** `HubModuleGrant.subject_id` es siempre una persona, y
>    encima es un `uuid5` derivado del claim del token —porque «no hay una tabla de usuarios única»,
>    dice su docstring—, así que se pueden leer las concesiones que existen pero no enumerar a quién
>    concederlas.
>
> **La decisión de diseño que unifica el ahora y el futuro** (usuario, 2026-08-22): no son dos
> sistemas, es **declarar quién es la autoridad** de los permisos —la aplicación o el IdP— y permitir
> que el sujeto de una concesión sea **una persona o un grupo**. Con eso, pasar al modelo del ERP no
> reescribe nada: se concede al grupo en vez de a la persona y se cambia la autoridad. Y **el grupo
> entra desde el principio, también en la interfaz** (decisión del usuario): no se deja para una
> migración futura.
>
> La semántica de la unión es la que ya usa `assert_chatbot_access` —rol **o** grupo, lo que case
> primero— con su regla documentada, que aquí vale igual: **sin concesión que case no hay módulo; el
> vacío es «nadie», no «todos»**.
>
> **Prerrequisito del usuario para IDE.5**: qué grupos declara hoy el IdP institucional en el atributo
> `SAML_ATTR_GROUPS`, y cuáles de ellos sirven para repartir módulos. Sin esa lista, la rama de grupo
> se construye y se prueba con dobles, pero no se verifica contra el IdP real — que es en cualquier
> caso una prueba manual humana, de las que `AGENTS.md` reserva a una persona.

### Prompt IDE.1 (RED/GREEN) — Quién manda sobre el rol: la aplicación o el IdP

**Modelo sugerido**: **Opus** — decide la forma de un ajuste que gobierna la autenticación, y el modo
de fallo es «alguien se queda fuera» o «alguien entra con más permiso del que debe».

```
# PROMPT IDE.1 (RED/GREEN) — El alta automatica deja de pisar el rol puesto a mano
# Deploy: cloud

## Por que
`identity_service._provision_sso_user`, en la rama del usuario que ya existe, hace `sso.role =
resolve_role(attributes)` sin condicion. Es correcto si la autoridad de los permisos es el IdP,
y es una averia si la autoridad es la aplicacion: cualquier rol asignado a mano dura hasta el
siguiente inicio de sesion.

Hoy no hay forma de decir cual de las dos cosas quiere el despliegue, asi que el codigo elige
por su cuenta, y elige la que el usuario NO quiere de momento.

## Que hacer
1. Un ajuste explicito que diga quien manda. Nombre y forma, a decidir y **razonar en el
   commit**: un `IDENTITY_AUTHORITY=app|idp` global, o por campo (`SAML_SYNC_ROLE`,
   `SAML_SYNC_ORGANIZACION`). Lo segundo es mas fino y mas verboso; lo primero es una linea y
   mete el rol y la organizacion en el mismo saco.
2. Con autoridad `app`: al crear la fila se usa `resolve_role` (no hay nada mejor que usar);
   al reencontrarla, **el rol no se toca**. `display_name`, `external_id` y `last_login_at` se
   siguen refrescando: son identidad, no permiso.
3. Con autoridad `idp`: comportamiento actual, sin cambios.
4. **Decidir y documentar que pasa con `organizacion_id`.** Hoy se refresca siempre, y el
   comentario dice por que: si el despliegue la configura despues, la persona no tiene que
   esperar a que alguien le toque la fila; y si se retira, deja de tener acceso. Esa razon
   sigue siendo buena — pero si un dia una organizacion se asigna a mano, chocara. Dejarlo como
   esta y decir por que, o meterlo en el ajuste. No dejarlo sin decidir.
5. El valor por defecto es `app`, que es lo que el usuario quiere ahora. Decirlo en
   `.env.example` con una frase que explique la consecuencia de cada valor.

## Tests (RED primero)
- RED: con autoridad `app`, un usuario con rol `admin` puesto a mano entra por SSO con una
  asercion que dice `user` y **sigue siendo `admin`**. Este es el test del bloque.
- RED: con autoridad `idp`, el mismo caso lo degrada a `user` (comportamiento actual intacto).
- RED: con autoridad `app`, un usuario **nuevo** se crea con el rol que resuelva la asercion.
- RED: en los dos modos, `display_name` y `last_login_at` se refrescan.
- RED: un valor desconocido del ajuste no se interpreta: falla al arrancar, no adivina.

## Criterio de done
- [ ] El rol puesto a mano sobrevive a un inicio de sesion por SSO
- [ ] Los dos modos con test propio, y el actual sin cambiar de comportamiento
- [ ] `.env.example` explica la consecuencia de cada valor
```

### Prompt IDE.2 (RED/GREEN) — `HubSsoUser` no es de SSO: es la tabla de usuarios

**Modelo sugerido**: **Opus** — renombra una tabla con datos y decide qué se lleva por delante.

```
# PROMPT IDE.2 (RED/GREEN) — Un registro de personas, con su origen anotado
# Deploy: cloud

## Por que
`HubSsoUser` tiene correo unico, nombre, rol, organizacion, activo y ultimo acceso. Es una
tabla de usuarios completa; se llama asi porque su unico escritor es el ACS de SAML. Mientras
el nombre diga «SSO», nadie va a escribir ahi una persona dada de alta a mano, y el proximo que
lo necesite creara una segunda tabla — que es como se llega a las cuatro que ya hay
(`SuperAdminAccount`, `AdminAccount`, `ClientAccount`, `HubSsoUser`).

## Que hacer
1. Renombrar el modelo y la tabla a `HubUser` / `hub_users`, con migracion Alembic que **renombra**
   —no crea y copia—, para no tocar los datos.
2. Anadir `origen`: `sso` | `manual`. Las filas existentes son `sso`. **Como dato con
   `CheckConstraint`, no como `Enum` de Python**: son dos valores estables, cada uno con
   consumidor en el codigo, mismo criterio que `purpose` en `HubLLMConfig`.
3. `grep -r` de `HubSsoUser` y `hub_sso_users`, y actualizar todo: `identity_service`, el ACS,
   tests. No dejar alias ni re-exportaciones (`AGENTS.md`: sin shims).
4. **No unificar todavia las otras tres tablas.** `user_to_uuid` esta en la propiedad de los
   workspaces de redaccion, en los PAT y en las concesiones, y SEC.8.1 tuvo que aceptar **las
   dos formas** en que quedo escrita la propiedad (`es_propietario` compara con el `user_id` tal
   cual y con su uuid5). Unificar eso es una migracion de datos con riesgo, y no es lo que
   pide este bloque. Anotarlo como trabajo propio en el informe de cierre.

## Tests (RED primero)
- RED: un test de infra falla si reaparece `HubSsoUser` o `hub_sso_users` en el codigo.
- RED: la migracion renombra y revierte sobre una base con filas dentro, sin perder ninguna.
- RED: las filas preexistentes quedan con `origen = 'sso'`.
- RED: `origen` no admite un valor fuera de los dos (lo rechaza la base de datos).
- RED: el ACS de SAML sigue aprovisionando igual.

## Criterio de done
- [ ] Migracion aplicada, `alembic current` en el informe, y `downgrade` probado
- [ ] `grep -r` a cero de los nombres viejos
- [ ] Ninguna fila perdida: recuento antes y despues
```

### Prompt IDE.3 (RED/GREEN) — Dar de alta a una persona, y que el SSO la reconozca

**Modelo sugerido**: **Opus** — el punto donde se cruzan el alta manual y el aprovisionamiento
automático es exactamente donde se cuelan los agujeros de autenticación.

```
# PROMPT IDE.3 (RED/GREEN) — Alta manual con rol; el SSO identifica, no crea
# Deploy: cloud

## Por que
Hoy una persona solo existe si entra por SSO, y entra con el rol que diga la asercion —por
defecto `user`—. Promocionar a alguien exige un UPDATE a mano en Postgres. Con IDE.1 el rol ya
sobrevive; falta poder ponerlo **antes** de que la persona entre.

Si el alta manual crea la fila primero, el inicio de sesion por SSO **la encuentra** por correo
en vez de crearla, y la persona entra con el rol, la organizacion y los modulos que ya le
pusieron. Eso es exactamente «dar usuarios con roles manualmente y que el SSO se utilice para
identificar».

## Que hacer
1. Endpoints de alta, edicion y desactivacion sobre `hub_users`, con `origen = 'manual'`:
   correo, nombre, rol, organizacion, activo.
2. El correo es la clave del reencuentro y ya es unico en la tabla. **Normalizarlo** al guardar
   y al buscar (minusculas, sin espacios): `Fabra@uji.es` y `fabra@uji.es` tienen que ser la
   misma persona, o el alta manual no sirve de nada.
3. **Sin contrasena.** Un alta manual no crea una credencial: crea la identidad y sus permisos.
   Quien entra, entra por SSO. Decirlo en la pantalla y en el docstring, porque la ausencia de
   contrasena se lee como un olvido si no esta explicada.
4. `is_active = false` **niega la entrada**, no solo oculta la fila. Comprobarlo en el ACS: hoy
   `is_active` existe y hay que verificar que alguien lo mira.
5. Reservado a superadmin. Un admin que pudiera crear usuarios con rol podria crear un admin.
6. Auditoria: quien dio el alta y cuando. `HubModuleGrant` ya lleva `granted_by` con el
   argumento escrito —«un permiso sin autoria no se puede auditar»—; aqui vale igual.

## Tests (RED primero)
- RED: alta manual con rol `admin`; la persona entra por SSO y **es** `admin`.
- RED: el reencuentro es por correo normalizado: alta con `Fabra@UJI.es`, entrada con
  `fabra@uji.es`, y **no** se crea una segunda fila.
- RED: una persona desactivada no puede iniciar sesion, aunque el IdP la valide.
- RED: un admin recibe 403 al intentar dar de alta a alguien.
- RED: el alta no crea ninguna credencial ni acepta un campo de contrasena.
- RED: dos altas con el mismo correo no crean dos filas.

## Criterio de done
- [ ] Alta manual + entrada por SSO verificadas de punta a punta
- [ ] `is_active = false` cierra la puerta, con test
- [ ] Contrato regenerado
```

### Prompt IDE.4 (RED/GREEN) — La pantalla de personas

**Modelo sugerido**: **Sonnet** — pantalla sobre endpoints ya construidos y decisiones ya tomadas.

```
# PROMPT IDE.4 (RED/GREEN) — Quien existe en esta plataforma
# Deploy: cloud

## Por que
No hay ninguna pantalla de usuarios. Quien administra la plataforma no sabe quien tiene cuenta,
ni con que rol, ni si entro alguna vez — y para averiguarlo necesita acceso a Postgres, que es
justo lo que no puede pedirse a otra administracion que despliegue esto.

## Que hacer
1. `/plataforma/usuarios`: listado con correo, nombre, rol, organizacion, **origen**
   (`manual` | `sso`), activo y ultimo acceso. Alta, edicion y desactivacion desde ahi.
2. Marcar de forma visible **quien manda sobre el rol** en este despliegue (el ajuste de IDE.1):
   con autoridad `idp`, editar el rol a mano es tirar el trabajo, y la pantalla tiene que
   decirlo en vez de dejar que alguien lo descubra al siguiente inicio de sesion.
3. Las otras tres tablas de identidad (`SuperAdminAccount`, `AdminAccount`, `ClientAccount`)
   **no se listan aqui**: siguen sin unificar (IDE.2, punto 4). Decirlo en la pantalla, con una
   linea, para que nadie lea el listado como «todas las cuentas de la plataforma».
4. Buscador por correo y nombre. Con una institucion entera dentro, un listado plano no sirve.
5. Reservado a superadmin, como los endpoints.

## Tests (RED primero)
- RED: el listado pinta las columnas iterando la respuesta del servidor, no una lista escrita.
- RED: un admin no puede abrir la pantalla.
- RED: la pantalla dice cual es la autoridad del rol, y cambia el aviso segun el ajuste.
- RED: desactivar a alguien se refleja en el listado sin recargar a mano.

## Criterio de done
- [ ] Alta, edicion y desactivacion verificadas en navegador
- [ ] La puerta de accesibilidad del proyecto, verde
- [ ] Cero literales sin i18n
```

### Prompt IDE.5 (RED/GREEN) — Conceder un módulo a una persona o a un grupo

**Modelo sugerido**: **Opus** — cambia el modelo de autorización de la plataforma; la unión y su
regla de fallo cerrado son el sitio donde un error abre acceso.

```
# PROMPT IDE.5 (RED/GREEN) — El sujeto de una concesion puede ser un grupo del IdP
# Deploy: cloud

## Por que
`HubModuleGrant.subject_id` es siempre una persona, asi que conceder modulos es insertar una
fila por cabeza. El usuario quiere que en el futuro los permisos vengan del ERP a traves de un
grupo declarado por el IdP — y ese transporte **ya existe**: `saml_groups` viaja en el claim
`groups` del JWT y el modo `restricted` de un chatbot ya lo consume.

**El grupo entra desde el principio, tambien en la interfaz** (decision del usuario,
2026-08-22): dejarlo para despues convierte el paso al modelo del ERP en una migracion en vez
de un cambio de pantalla.

## Que hacer
1. `subject_type` en `hub_module_grants`: `usuario` | `grupo`, con `CheckConstraint`. Las filas
   existentes son `usuario`. La restriccion unica pasa a ser
   `(subject_type, subject_id, module_code)`.
2. **Ensanchar `subject_id`.** Hoy es `String(36)`, dimensionado para un UUID. Un nombre de
   grupo del IdP no cabe ahi de forma fiable: a 255. Sin esto, el primer grupo con nombre largo
   se corta o revienta el INSERT.
3. `modulos_del_usuario` une dos consultas: las concesiones de tipo `usuario` con el
   `subject_id` de esta persona, y las de tipo `grupo` cuyo `subject_id` este en sus
   `saml_groups`. Sigue filtrando por `vigente` y sigue siendo **fallo cerrado**: sin
   concesion que case, no hay modulo. Es la misma semantica de `assert_chatbot_access` —rol o
   grupo, lo que case— y su trampa documentada aplica igual: el vacio es «nadie», no «todos».
4. **Comparacion de grupos: decidir y razonar en el commit** si es sensible a mayusculas. Los
   IdP no se ponen de acuerdo; elegir y dejarlo escrito es mejor que descubrirlo en produccion.
5. `/plataforma/modulos`: conceder y retirar, eligiendo si el sujeto es una persona —del listado
   de IDE.4— o un grupo, escrito a mano. El catalogo de modulos se lee de
   `HubPlatformModule` con `vigente`, **nunca de una lista en el frontend**.
6. En la ficha de una persona, mostrar sus modulos **y de donde le vienen**: concedidos a ella o
   heredados de un grupo. Un permiso cuyo origen no se ve es un permiso que nadie se atreve a
   retirar.
7. Reservado a superadmin. Y decir en la pantalla que el superadmin **no necesita concesion**,
   con su razon —una instalacion nueva se quedaria con el superadmin encerrado fuera—, para que
   nadie busque su fila.
8. Retirar una concesion de grupo afecta a todo el grupo: **pedir confirmacion diciendo a
   cuantas personas conocidas afecta**, no un «seguro?» a secas.

## Tests (RED primero)
- RED: una persona sin concesion propia, con un `saml_group` que si la tiene, **obtiene el
  modulo**. Es el test del bloque.
- RED: retirada la concesion del grupo, lo pierde en la misma peticion siguiente.
- RED: dos vias que concedan lo mismo no duplican el modulo en la respuesta.
- RED: un grupo que la persona no tiene no le concede nada.
- RED: un modulo con `vigente = false` no se concede por ninguna de las dos vias.
- RED: las concesiones existentes (tipo `usuario`) siguen funcionando igual tras la migracion.
- RED: un nombre de grupo de mas de 36 caracteres se guarda y se recupera entero.
- RED: la ficha de la persona dice, por cada modulo, si es propio o heredado de que grupo.
- RED: un admin recibe 403 al conceder.

## Criterio de done
- [ ] Migracion aplicada, `alembic current` en el informe, `downgrade` probado
- [ ] Concesion por persona y por grupo verificadas en navegador
- [ ] El origen de cada modulo visible en la ficha
- [ ] Cero codigos de modulo escritos en el frontend
```

> **Este bloque va ANTES del despliegue** (decisión del usuario, 2026-08-22): «no tiene sentido hacer el
> deploy de una aplicación con una estructura y unos mecanismos de identificación que no son los que se
> van a utilizar». El argumento se sostiene solo: IDE.2 renombra una tabla, IDE.5 cambia el esquema de
> las concesiones e IDE.1 cambia el comportamiento de la autenticación. Migración de esquema, cambio de
> autorización y renombrado son las tres cosas que salen baratas **antes** de que haya personas reales
> dentro, y caras después.
>
> **Requiere PLAT.1 y PLAT.2 hechos**: las pantallas de IDE.4 e IDE.5 viven en `/plataforma`, la sección
> que crea PLAT.2. El resto de PLAT va después de este bloque. Orden completo:
> PLAT.1 → PLAT.2 → **IDE.1…IDE.5** → PLAT.3…PLAT.7 → Deploy.
>
> **Y deja una consecuencia para el despliegue**: IDE.1 introduce un ajuste nuevo (la autoridad del
> rol), así que el inventario de variables de entorno del bloque Deploy tiene que incluirlo. Un
> despliegue que lo omita se queda con el valor por defecto sin que nadie lo haya decidido.
>
> **Orden y dependencias.** **IDE.1 primero, y sin él el bloque no tiene sentido**: mientras el alta
> automática pise el rol, cualquier pantalla de usuarios es decorativa. IDE.2 es el renombrado y va
> antes de IDE.3, que escribe en esa tabla. IDE.4 depende de IDE.3 y es el único prompt barato del
> bloque. IDE.5 es independiente de IDE.2–IDE.4 en el backend —toca otra tabla— pero su pantalla
> necesita el listado de personas de IDE.4, así que va al final.
>
> **Qué no hace este bloque, dicho a propósito.** No unifica las cuatro tablas de identidad:
> `user_to_uuid` está en la propiedad de los workspaces de redacción, en los PAT y en las
> concesiones, y `es_propietario` ya tiene que aceptar las dos formas en que quedó escrita la
> propiedad (SEC.8.1). Eso es una migración de datos con riesgo real y merece su propio bloque, con
> su inventario antes de tocar nada. Y no reparte un IdP entre varias organizaciones:
> `HubSsoUser.organizacion_id` sale de `SAML_ORGANIZACION_ID`, o sea de la configuración del
> despliegue, así que hoy un IdP se asocia a **una** organización. Con un piloto de una sola
> institución no molesta; con dos, hay que decidirlo antes de escribirlo.

---
