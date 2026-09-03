# Quién es una cuenta de administración (decisión de USR.6)

> **Escrito el 2026-09-03**, al ejecutar el prompt USR.6 del Bloque USR. Es la decisión que el
> prompt exigía tomar **antes** de escribir código, porque condiciona todo lo que venga detrás.

## El problema, medido y no supuesto

Tres cosas que no se podían hacer, y una que se hizo por eso:

1. **No hay ningún endpoint que cree un `AdminAccount`.** Sólo lo hacen `seeds.py` (la cuenta de
   desarrollo `partner_dev`) y `bootstrap.py` (que crea un **superadministrador**, no un
   administrador). Dar de alta a alguien exigía un script contra la base de datos.
2. **Una organización tiene exactamente un administrador posible.** `AdminAccount.partner_id` es
   la **clave primaria** y el enlace con las organizaciones es `HubOrganizacion.partner_id`. La
   relación es *un partner → muchas organizaciones*, así que «cuatro personas administrando la
   UJI» no es representable: serían cuatro `partner_id` distintos y tres abrirían el panel con la
   lista de asistentes vacía.
3. **No hay forma de cambiar la contraseña de un superadministrador** desde la aplicación:
   `PATCH /auth/admins/{partner_id}/password` cubre administradores y nada más.

Y la consecuencia, que está en producción: el 2026-09-01 los **seis probadores del piloto** se
crearon como `SuperAdminAccount` con una contraseña compartida, porque era la única forma de que
entraran y vieran algo. Seis personas con poderes de plataforma completos y sin atribución por
persona.

### El recuento que decide el coste

En **producción**, el 2026-09-03:

| Tabla | Filas |
|---|---|
| `superadminaccount` | **7** (la propia y los seis probadores) |
| `adminaccount` | **0** |
| `clientaccount` | **0** |
| `hub_users` | **0** |

Esto es lo que hace la decisión barata: **`adminaccount` está vacía**, así que cambiar qué tabla
es la identidad de administración **no migra ni una fila**.

## Las dos opciones

### (a) Tabla puente `admin_organizaciones`

Conservar `AdminAccount` como identidad y añadir una muchos-a-muchos con las organizaciones.

- **A favor**: cambio local y pequeño; no toca el login ni el ACS.
- **En contra**: **consolida cuatro tablas de identidad**. La contraseña, el rol y la organización
  de una persona quedan repartidos según por qué puerta entró, y la pantalla de personas tendría
  que enseñar dos clases de administrador —el de `adminaccount` y el `HubUser` con rol admin—
  distinguiéndolos para siempre. Y **no cierra la deuda de las seis cuentas elevadas**: habría
  que hacer las dos cosas.

### (b) `HubUser` con `role='admin'` es la identidad de administración

`AdminAccount` se queda con lo que de verdad es suyo —el partner, los créditos, la facturación— y
deja de ser una identidad de login.

- **A favor**: es la dirección que el propio docstring de `HubUser` ya señalaba; **cierra la deuda
  de las seis cuentas elevadas sola**, porque esas personas pasan a ser `HubUser` con su rol real;
  y con `adminaccount` vacía no hay migración de datos.
- **En contra**: más superficie tocada, y deja abierto un caso que (a) resolvía —una persona
  administrando **varias** organizaciones—.

## Decisión: **(b)**

Y no por elegancia: por el recuento. Con `adminaccount` vacía, (b) cuesta cero migración, y (a)
costaría mantener dos clases de administrador **para siempre** además de arreglar aparte las seis
cuentas del piloto.

### Lo que (b) ya es verdad hoy, después de USR.1–USR.3

No hay que construirlo: hay que **comprobarlo**, y de eso se encargan los tests de este prompt.

| Capacidad | Cómo se resuelve |
|---|---|
| Alta desde el panel | `POST /hub/users` con `role='admin'` (IDE.3) y la pantalla de Personas |
| Contraseña local | `PATCH /hub/users/{id}/password` (USR.1), que un admin puede usar sobre su organización |
| Entrada | `POST /auth/user/login` (USR.2), que emite el rol real y la organización |
| Reencuentro por SSO | el ACS provisiona o encuentra el `HubUser` por correo |
| **Varias personas por organización** | muchas filas de `hub_users` con el mismo `organizacion_id` |
| Acotación por organización | `organizacion_ids` del token + `core/auth/tenancy.py` |
| Módulos concedidos | `HubModuleGrant.subject_id` = **el propio UUID** de la fila, porque `user_to_uuid` de un UUID devuelve ese UUID |
| Crear un superadministrador | `POST /hub/users` con `role='superadmin'` y su contraseña por USR.1 |

Nótese lo último: **la tercera cosa que no se podía hacer ya se puede**. Un superadministrador
nuevo se crea desde el panel y se le fija la contraseña; `superadminaccount` se queda sólo con la
cuenta de instalación, que es lo que `bootstrap.py` crea y lo que la pantalla de Personas enseña
en solo lectura.

### Lo que (b) deja abierto, y su camino

**Una persona administrando varias organizaciones.** `HubUser.organizacion_id` es una clave ajena
única. Cuando haga falta —un partner con varias administraciones, no la UJI del piloto—, el camino
es una tabla puente `hub_user_organizaciones` que **sustituya** a esa columna, con la cascada de
`organizacion_ids` leyéndola al emitir el token. **No** es volver a `AdminAccount`: sería la misma
tabla puente de (a) pero sobre la identidad buena.

No se hace ahora porque no hay ningún caso: hoy es una organización por persona y el piloto es de
una sola organización. Hacerlo hoy o cuando aparezca cuesta lo mismo, porque la columna es
anulable y la lectura del claim está en un solo sitio.

### Lo que este prompt NO hace, y por qué

**Retirar el login de `AdminAccount`** (`POST /auth/admin/login`, `setAdminPassword`, la rama del
ACS y `_orgs_del_admin`). Es la consecuencia lógica de (b) y hay que hacerla, pero es un cambio de
comportamiento con superficie propia: dos endpoints, dos ramas del ACS, la tercera puerta del
formulario de login, la cuenta de desarrollo de `seeds.py` y sus tests. Meterla en el mismo prompt
que la decisión mezclaría «decidir» con «desmontar», y el prompt ya avisaba: *si (b) no cabe en un
bloque, se parte — pero se parte hacia (b), no se hace (a) «de momento»*.

Queda por tanto **partido hacia (b)**, y lo que falta es exactamente esto:

- [ ] Retirar `POST /auth/admin/login` y `PATCH /auth/admins/{partner_id}/password`.
- [ ] Retirar la rama de `AdminAccount` del ACS de SAML y su `_orgs_del_admin`.
- [ ] Quitar la segunda puerta del `LoginPage` (quedarían superadmin y persona).
- [ ] `seeds.py`: la cuenta de desarrollo pasa a ser un `HubUser` con `role='admin'`.
- [ ] `AdminAccount` se queda sin `email` ni `hashed_password`: es partner y facturación.

### Un hueco que apareció al verificar, y que tampoco se cierra aquí

**La pantalla de Personas es sólo de superadministrador, así que un admin no puede llegar a la
capacidad que USR.1 le dio.** `PATCH /hub/users/{id}/password` **sí** le deja fijar la contraseña
de alguien de su organización —y ése era su argumento: quien da de alta a sus probadores es quien
administra su organización—, pero `GET /hub/users` exige superadministrador, así que desde el
panel no ve la lista sobre la que actuar. Hoy la capacidad existe **por API y no por pantalla**.

No se ensancha aquí porque el propio router tiene escrita la razón contraria y es buena: «un admin
que pudiera crear personas con rol podría crearse un admin». La forma correcta no es abrir la
pantalla entera, sino partirla: **listar y fijar contraseña** acotado por tenencia sí, y **crear o
cambiar roles** no. Eso es una decisión de permisos con peso propio, nadie la ha pedido todavía, y
mientras el superadministrador dé de alta a los probadores del piloto no bloquea nada.

Mientras eso no se haga, **las dos vías conviven**: un `AdminAccount` sigue entrando por su puerta
y un `HubUser` con rol admin por la suya. No es una contradicción, es una transición con la
dirección escrita.

Y lo que **tampoco** hace, por decisión del propio prompt: unificar `ClientAccount` ni la
propiedad de los workspaces de redacción (`user_to_uuid`, SEC.8.1). Ésa es la parte con riesgo
real y merece bloque propio con su inventario delante.

## Cómo se deshace la deuda de las seis cuentas del piloto

Con (b) el camino es directo y no necesita código nuevo:

1. Crear cada persona en la pantalla de Personas con su rol real —`informer` para quien anota,
   `admin` para quien administre la UJI— y la organización Universitat Jaume I.
2. Fijarle su contraseña, distinta por persona.
3. Retirar su `SuperAdminAccount`.

El paso 3 es el único que hoy no tiene superficie en el panel: la pantalla enseña esas filas en
solo lectura porque viven en otra tabla. Se hace desde el servidor, y desaparece cuando la lista
del punto anterior se complete.

Ver `planificacion/PROJECT_STATE.md` (Bloque USR) y `docs/MULTITENENCIA.md`.
