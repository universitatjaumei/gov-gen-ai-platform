## Bloque MT — Multitenencia real: qué está aislado y qué no (PENDIENTE, planificado el 2026-08-23)

Nace de una pregunta del usuario que vale más que los tres prompts de arriba: «cambio de
organización y sigo viendo los mismos proveedores y modelos, las mismas personas, los mismos
chatbots, los mismos prompts». El objetivo del diseño es que **una Diputación pueda desplegar
una instancia por municipio**, con un superadministrador que da de alta organizaciones y un
administrador por organización cuyas personas sólo ven lo suyo.

### Lo que la auditoría del 2026-08-23 encontró

**Lo que sí está bien** y conviene no tocar: el **núcleo operativo** está acotado, unas veces por
`organizacion_id` y otras por el camino `chatbot_id` / `site_id` — chatbots, corpus, ingesta,
vigencia, curación, temas, vocabulario, interacciones, feedback, escenarios de prueba, chat y
cuotas—. Doce routers pasan por la capa de tenencia y `test_tenant_isolation.py` lo vigila. Eso
es lo que filtraría contenido **entre municipios**, y no lo hace.

**Lo que no**, con el detalle medido:

1. **Modelos y proveedores son globales.** `hub_providers` (4 filas, y una de sus columnas es
   `api_key`) y `hub_llm_configs` (7 filas repartidas en tres niveles) no tienen organización ni
   camino hacia una. Una sola credencial para todos: en el modelo Diputación→municipios eso es
   incorrecto por coste —el consumo de un municipio se factura al contrato de otro— y por
   protección de datos, porque los prompts de un ayuntamiento viajan por el contrato ajeno.
   `get_model_for_tier(tier, provider)` no recibe organización, y lo llaman **8 ficheros**.
2. **El módulo Informes no tiene dimensión de organización, en absoluto.** `owner_kind` admite
   `user`, `platform` y `superadmin`: **no existe `organizacion`**. Una plantilla es de una
   persona o de todo el mundo. Son **51 endpoints y 7 modelos**.
3. **Personas: el dato está y el filtro no.** `hub_users.organizacion_id` existe con su clave
   ajena; `list_users` no filtra y además es sólo de superadministrador, así que **un
   administrador no puede gestionar a la gente de su propia organización**.
4. **Concesiones de módulo y tokens van por sujeto, sin organización.** Una concesión dice
   «informes», no «informes en el ayuntamiento de X».
5. **Prompts de actividad, globales por diseño.** Defendible para actividades de plataforma;
   discutible cuando un municipio quiera su propia redacción.
6. **El superadministrador lo ve todo y el selector no filtra.** `scope_query_to_orgs` no acota a
   un superadministrador, **y eso es correcto como permiso**. Lo que falta es lo otro: una
   **vista** que diga «ahora estoy trabajando sobre Vila-real». REV.10 puso el selector; nadie lo

### Decisión del usuario (2026-08-23): la fase 1 va ANTES del piloto

El corte no es por importancia, sino **por migración**. Añadir una columna a una tabla vacía es
gratis; añadirla cuando el piloto lleva meses de informes firmados y corpus cargado es una
migración de datos con riesgo. El piloto de la UJI es de una sola organización, así que en
funcionamiento nada de esto le afecta: lo único que le afecta es el orden.

**Invariante de la fase 1, y es lo que la hace segura**: `organizacion_id` nulo significa «nivel
plataforma» y se hereda, igual que la cascada de temas. Con todas las filas existentes a nulo, el
piloto se comporta **exactamente** como hoy. Si la Diputación no llega nunca, la fase 1 no habrá
estorbado a nadie y no se habrán construido pantallas para un cliente que no existe.

**Lo que ya está hecho y no hay que planificar**: las cuotas. `hub_usage_counters.subject_type`
admite `organizacion` desde SEC.4, y hay tests que lo ejercitan (`test_should_429_when_
organizacion_monthly_quota_exceeded`). No se toca.

---

#### MT fase 1 — el esquema (ANTES del piloto). 7 prompts

##### Prompt MT.1 (RED/GREEN) — La regla del ámbito, escrita una vez y vigilada

**Modelo sugerido**: **Opus** — es la pieza de la que dependen las seis siguientes, y un
guardarraíl mal planteado da falsos positivos y acaba desactivado.

**Objetivo**: la cascada «nulo = plataforma, se hereda» ya existe **tres veces** —temas
(`hub_themes`), valores por defecto de RAG (`HubOrganizacion.default_*`) y vocabulario— y cada
una la implementa a su manera. Antes de añadirla a cinco tablas más, se escribe una vez.

Y se pone un guardarraíl que **obligue a toda tabla nueva de configuración a declarar su
ámbito**, que es lo que habría evitado esta auditoría: `hub_llm_configs` nació global sin que
nadie lo decidiera, simplemente porque no había dónde decir lo contrario.

```
# PROMPT MT.1 — Que el ámbito de una tabla sea una decisión y no un olvido
# Deploy: shared (la regla la usan cloud y edge)

## RED
- `test_should_resolve_the_organisation_level_over_the_platform_one`: dada una fila de
  organización y otra de plataforma, gana la de organización campo a campo.
- `test_should_fall_back_to_the_platform_row`: sin fila de organización, la de plataforma.
- `test_should_not_merge_across_organisations`: la fila de otra organización no participa.
  **Este es el test que importa**: una resolución que ordene mal el `ORDER BY` puede devolver
  la configuración del municipio de al lado sin que nada falle.
- `test_should_declare_the_scope_of_every_config_table`: recorre los modelos de
  `HubConfigBase` y exige que cada uno declare su ámbito —`plataforma`, `organizacion` o
  `heredable`— en un atributo de clase. Una tabla nueva sin declararlo pone el test rojo.

## GREEN
- `core/tenancy/ambito.py` con el resolvedor y el enum de ámbitos.
- Las tres cascadas que ya existen **no se reescriben aquí**: se anota cuál sustituirá a cuál
  y se hace en su prompt, para que este no toque comportamiento.

## Cierre
- [ ] El guardarraíl caza una tabla sintética sin ámbito declarado
```

##### Prompt MT.2 (RED/GREEN) — Proveedores y modelos dejan de ser globales

**Modelo sugerido**: **Opus** — es el único cambio de la fase con efecto real, y toca la
resolución que usan los tres módulos.

**Objetivo**: `hub_providers` tiene cuatro filas y una de sus columnas es `api_key`. Una sola
credencial para todos significa que, en el modelo Diputación→municipios, el consumo de un
ayuntamiento se factura al contrato de otro y sus prompts viajan por ese contrato. No es
incomodidad: es coste mal atribuido y protección de datos.

`hub_llm_configs` es lo mismo un escalón arriba: siete filas en tres niveles, un juego para todos.

```
# PROMPT MT.2 — Cada organización con su proveedor y sus niveles
# Deploy: cloud (configuración) — la consume edge por ConfigProvider

## RED
- `test_should_prefer_the_organisation_provider_over_the_platform_one`
- `test_should_fall_back_to_the_platform_provider`: sin proveedor propio, el de plataforma.
  Es lo que hace que el piloto siga funcionando sin tocar una fila.
- `test_should_not_leak_an_api_key_across_organisations`: **el test que justifica el prompt**.
  Resolver para la organización A nunca puede devolver la credencial de B.
- `test_should_keep_one_default_per_tier_and_scope`: la unicidad de `is_default` pasa a ser
  por (nivel, ámbito). Hoy es global y dos organizaciones no podrían tener cada una su
  modelo por defecto.
- `test_should_migrate_existing_rows_to_the_platform_level`: las 11 filas existentes quedan
  a nulo, que es «plataforma».

## GREEN
- Migración: `organizacion_id` nullable en las dos tablas, índice, y la restricción única de
  `is_default` reescrita por (tier, organizacion_id).
- El resolvedor de MT.1 aplicado en `ConfigProvider`.

## Cierre
- [ ] `alembic downgrade` limpio
- [ ] Suite completa: el comportamiento del piloto no cambia
```

##### Prompt MT.3 (RED/GREEN) — La organización llega hasta el modelo

**Modelo sugerido**: **Opus** — ocho llamadores y tres módulos; el riesgo es dejar uno con la
resolución vieja y no enterarse.

**Objetivo**: `get_model_for_tier(tier, config_provider)` **no recibe la organización**, así que
MT.2 no serviría de nada: la cascada estaría en la base y nadie le diría contra qué organización
resolver. Lo llaman ocho ficheros —ingesta, copiloto, scripts, borradores, espacios de trabajo,
el despachador de rastreo y el propio `model_factory`—.

```
# PROMPT MT.3 — Quien pide un modelo dice para quién
# Deploy: shared

## RED
- `test_should_require_the_organisation_to_resolve_a_tier`: la firma la exige. No un
  parámetro opcional con defecto: un opcional se olvida y el fallo es silencioso —resuelve
  plataforma cuando debía resolver la organización— y eso no lo caza ningún test.
- Un test por llamador que fije **de dónde** saca cada uno la organización: la ingesta del
  chatbot, los de Informes del espacio de trabajo, el rastreo del sitio.
- `test_should_have_no_caller_left_on_the_old_signature`: `grep` a cero.

## GREEN
- Firma nueva y los ocho llamadores.

## Cierre
- [ ] Suite completa verde con el comportamiento de hoy (todo a nivel plataforma)
```

### Reutilizar configuración entre organizaciones (planteado por el usuario el 2026-08-24)

Pregunta del usuario: en un despliegue de una Diputación para varios municipios —o de una empresa
que les preste servicio— tiene sentido **reutilizar plantillas de informe y configuración de
chatbots, nunca datos**. ¿Elevar a plataforma, o exportar e importar? Y añade que cuando existan
**automatizaciones** y **expedientes** hará falta también allí, y que en plantillas la elevación
es doble porque las diseña un usuario o un administrador.

Con cuatro módulos, esto no es una función: es un **mecanismo**, y conviene decidirlo una vez.

#### Lo que ya existe

**Las plantillas de informe ya tienen nivel de plataforma**: `owner_kind ∈ {user, platform,
superadmin}` más `is_global`, y `list_templates` devuelve `is_global OR owner_id == yo`. Lo que
falta es el escalón de en medio, que es lo que MT.4 añade. La doble elevación del usuario es, por
tanto, **usuario → organización → plataforma**, con el primero y el último ya construidos.

Los chatbots **no** lo tienen: `hub_chatbots.organizacion_id` es NOT NULL.

De paso, una redundancia que hay que limpiar al tocarlo: `is_global` se calcula en el router como
`owner_kind == "platform"`, así que dos columnas guardan el mismo hecho y pueden discrepar.

#### La distinción que decide el diseño

No es «compartir sí o no», es **compartir por referencia** frente a **copiar al instanciar**:

| | Una fila, muchos lectores | Una fila por organización |
|---|---|---|
| Sirve cuando | el objeto es **sólo configuración** | el objeto **acumula datos propios** |
| Arreglar el original | llega a todos | hay que reaplicarlo |
| Riesgo | quien edita lo cambia para todos | divergencia silenciosa |

| Módulo | Unidad reutilizable | Mecanismo | Por qué |
|---|---|---|---|
| **Informes** | plantilla (`spec_json`) | referencia + bifurcar al editar | es configuración; los informes son filas aparte |
| **Chatbots** | definición del asistente | **copia** | un chatbot posee corpus, conversaciones, feedback y clave de widget |
| **Automatizaciones** | script / flujo | referencia | el código es configuración; las ejecuciones son por organización |
| **Expedientes** | plantilla de procedimiento | referencia | el expediente es dato, y no se comparte nunca |

**Los chatbots son el caso que hay que no equivocar**: elevar un chatbot a plataforma no comparte
su configuración, comparte **el chatbot** —un corpus y un registro de conversaciones para todos
los municipios—, que es justo el «nunca datos». Lo que hace falta ahí es una *plantilla de
asistente* que cada organización materializa en su propio chatbot. Es coherente con la decisión
ya tomada de que **el corpus no se comparte entre chatbots**.

#### «Para todas» y «para un grupo», con un solo mecanismo

El usuario distingue configuraciones que valen para todas y otras que sólo para un grupo —«las que
compartan una herramienta de gestión»—. Eso no es un club, es **compatibilidad**: una plantilla
que lee exportaciones de G400 sólo sirve donde hay G400. Así que un solo eje:

- la organización declara **qué tiene** (`capacidades: {gestion: "G400"}`),
- el artefacto de catálogo declara **qué necesita** (`requiere: {gestion: "G400"}`),
- sin condiciones = para todas.

Frente a una tabla de grupos, esto evita que alguien mantenga la pertenencia a mano y que derive:
el sistema **deduce** quién puede consumirlo. Si algún día aparece un grupo arbitrario («los del
plan avanzado»), es otra etiqueta. **Comparación plana clave→valor, no expresiones**, que es lo que
impide que degenere en un motor de reglas.

#### Exportar/importar no es la alternativa: es el otro caso

- **Dentro de una instalación**: el nivel de plataforma es mejor, porque conserva la procedencia y
  permite propagar un arreglo.
- **Entre instalaciones** (una empresa con un despliegue `edge` por municipio, sin base común): el
  nivel de plataforma no existe, y exportar/importar es la **única** opción.

Y de aquí sale la decisión que hace barato el futuro: **la unidad de reutilización es un `spec`
serializable y versionado, no una fila a la que se apunta.** Con eso, exportar es escribir ese
mismo `spec` a un fichero. Las plantillas de informe ya lo son (`spec_json`); la configuración de
un chatbot está repartida en columnas, así que ahí el `spec` hay que definirlo — y es la razón de
que la plantilla de asistente sea tabla nueva y no un `organizacion_id` nullable en
`hub_chatbots`.

#### Qué entra ahora y qué no

Criterio de la fase 1: **coste de migración**, no importancia.

| Pieza | ¿Ahora? | Por qué |
|---|---|---|
| **Procedencia** (`derivado_de` + versión de origen) en lo que se instancia por copia | **Sí — MT.4.2** | Lo único **irrecuperable**: cuando los municipios tengan copias sin constancia de su origen, «la Diputación corrigió el prompt, propágalo» es imposible para siempre. Cuestan dos columnas nullable |
| Nivel `organizacion` en `owner_kind` + doble elevación | **Sí — MT.4** | CHECK y columna sobre tabla que tras el piloto tendrá filas vivas |
| El agujero de editar lo global | **Ya arreglado (2026-08-24)** | Era de hoy, no de mañana. Ver abajo |
| `capacidades` / `requiere` | **No** | Casi gratis ahora y casi gratis después: pocas filas y configuración. Va en la fase 2 (MT.17) |
| Catálogo, instanciación, pantallas, exportar/importar | **No** | Empiezan vacíos: cero riesgo de migración. Fase 2 (MT.18–MT.20) |

Orden de recorte si hay que ajustar: primero exportar/importar (diferirlo es gratis, es el mismo
`spec`), después el reparto por grupo. **La procedencia no se recorta**: es la más barata de
construir y la única cuyo olvido no se deshace.

#### Hallazgo del 2026-08-24: cualquier administrador podía retirar la plantilla de todos

Comprobado con tres tests antes de afirmarlo, y **arreglado en el momento** porque no era una
carencia futura sino un agujero en producción. `_exigir_admin` miraba **sólo el rol** y después
`_plantilla_o_404` traía la plantilla **por id, sin comprobar de quién es**. Resultado: un
administrador de cualquier organización podía renombrar la plantilla de plataforma, **archivarla**
—lo que la saca de la lista de todos y bloquea crear informes nuevos con ella— o renombrar la
plantilla personal de otra persona. Con una sola organización no se nota; en el modelo
Diputación→municipios, el administrador de un ayuntamiento retira la plantilla compartida de los
demás.

Cerrado con `_exigir_poder_sobre`: la de plataforma, sólo el superadministrador; la de una
persona, su dueño; un administrador sin relación con ella, 403. **El arreglo completo necesita
MT.4**: hasta que las plantillas tengan `organizacion_id`, «administrador» sólo significa
«administrador de algún sitio», y no hay contra qué comprobarlo. Cuando lo tengan, aquí entra el
administrador de la organización dueña.

---

##### Prompt MT.4 (RED/GREEN) — Informes gana la dimensión que no tiene

**Modelo sugerido**: **Opus** — 51 endpoints y 7 modelos; hay que decidir qué se acota ahora y
qué espera a la fase 2 sin dejar el esquema a medias.

**Objetivo**: `owner_kind` admite `user`, `platform` y `superadmin`. **No existe
`organizacion`**: una plantilla es de una persona o de todo el mundo. Es la carencia más
profunda de las seis, porque no es un filtro que falte sino una dimensión que no está.

Aquí se añade **sólo el esquema**: la UI y el filtrado van en la fase 2. Con `organizacion_id`
nulo, las 23 plantillas de hoy siguen siendo de plataforma o de su persona, como ahora.

**Ampliado el 2026-08-24** con la doble elevación que planteó el usuario: las plantillas las
diseña un usuario **o** un administrador, así que la escalera completa es **usuario →
organización → plataforma**, y los dos extremos ya existen. Lo que MT.4 añade es el escalón de en
medio; elevar y bajar por esa escalera es una operación, no un campo que se edita a mano.

```
# PROMPT MT.4 — Una plantilla puede ser de una organización
# Deploy: edge (los informes son datos del cliente)

## RED
- `test_should_accept_organizacion_as_an_owner_kind`
- `test_should_reject_an_organisation_owner_without_organizacion_id`: coherencia entre las
  dos columnas, en el modelo y en la base. Sin esto queda una plantilla «de organización» que
  no dice de cuál.
- `test_should_leave_existing_templates_untouched`: las 23 filas y sus versiones, intactas.
- `test_should_carry_the_organisation_into_the_workspace`: un informe hecho con una plantilla
  de organización pertenece a esa organización, no a la de quien lo abre.
- `test_should_keep_the_platform_level_visible_to_everyone`: **el que protege lo que ya
  funciona**. El nivel de plataforma existe desde antes de MT y es lo que permite que la
  Diputación comparta una plantilla; añadir el escalón de en medio no puede dejar de verlo.
- `test_should_let_an_admin_manage_only_the_templates_of_their_organisation`: aquí entra el
  administrador en `_exigir_poder_sobre`, que hoy no puede porque no hay columna contra la
  que comprobar (ver el hallazgo del 2026-08-24, arriba).
- `test_should_fork_when_editing_an_inherited_template`: editar lo heredado **bifurca**, no
  modifica el original. Sin esto, «reutilizable» significa «el primero que lo toque lo cambia
  para todos», y con `is_global` protegido a superadministrador el efecto sería el contrario:
  nadie puede adaptarlo.
- `test_should_collapse_is_global_into_one_source_of_truth`: `is_global` se calcula hoy en el
  router como `owner_kind == "platform"`. Dos columnas con el mismo hecho terminan
  discrepando; una de las dos manda, y lo dice un test.

## GREEN
- Migración sobre `hub_report_templates` y `hub_workspaces`; `CheckConstraint` del vocabulario
  de `owner_kind` ampliado.
- `_exigir_poder_sobre` completa con el eje de organización.

## Cierre
- [ ] Los 51 endpoints siguen respondiendo igual (fase 1 no cambia comportamiento)
- [ ] Las plantillas de plataforma siguen viéndose desde todas las organizaciones
```

##### Prompt MT.4.2 (RED/GREEN) — De dónde salió esta copia

**Modelo sugerido**: **Sonnet** — dos columnas y su significado; el alcance está cerrado.

**Objetivo**: es la **única** pieza de la reutilización cuyo olvido no se deshace. Lo que se
instancia por copia —un chatbot desde una plantilla de asistente, y luego los flujos y los
procedimientos— tiene que decir de dónde salió y con qué versión. Sin eso, en cuanto haya copias
repartidas, «la Diputación ha corregido el prompt del asistente, propágalo» deja de ser posible
para siempre: no hay forma de reconstruir el parentesco a posteriori.

Cuesta dos columnas nullable y no cambia comportamiento: hoy nada instancia nada, así que quedan
a nulo. Va **ahora** por eso: después habría que inventarse la procedencia de filas vivas.

```
# PROMPT MT.4.2 — La procedencia de lo copiado
# Deploy: cloud (chatbots) / edge (plantillas de informe)

## RED
- `test_should_record_where_a_copy_came_from`: `derivado_de` + `version_de_origen`.
- `test_should_survive_the_original_being_deleted`: `ON DELETE SET NULL`, no CASCADE. **Este
  es el test que importa**: con CASCADE, retirar la plantilla de la Diputación borraría los
  chatbots de los municipios. La procedencia es una anotación histórica, no una dependencia.
- `test_should_leave_everything_null_today`: nada instancia nada todavía.
- `test_should_tell_which_copies_are_behind`: dada una versión nueva del original, qué copias
  se quedaron en una anterior. Es la consulta para la que existen las dos columnas; sin ella
  serían dos campos que nadie lee.

## GREEN
- Migración: las dos columnas donde se instancia por copia.

## Cierre
- [ ] `alembic downgrade` limpio
```

##### Prompt MT.5 (RED/GREEN) — Una concesión dice en qué organización

**Modelo sugerido**: **Sonnet** — el modelo de IDE.5 ya distingue sujetos; esto añade un eje.

**Objetivo**: una concesión dice «informes», no «informes en el ayuntamiento de X». Con una
organización da igual; con veinte, conceder un módulo a un grupo del IdP se lo concede en todas.
Lo mismo con los tokens: `hub_personal_access_tokens` va por dueño y no dice sobre qué
organización puede actuar.

```
# PROMPT MT.5 — El permiso dice dónde
# Deploy: cloud

## RED
- `test_should_grant_a_module_only_in_one_organisation`
- `test_should_keep_a_null_organisation_meaning_everywhere`: las concesiones de hoy siguen
  valiendo en todas, que es lo que significan ahora. Reinterpretarlas en silencio sería
  cambiarle los permisos a alguien sin decírselo.
- `test_should_scope_a_token_to_an_organisation`
- `test_should_refuse_a_token_acting_outside_its_organisation`: **el test que importa**, y va
  contra el resolvedor real, no contra el DTO.

## GREEN
- `organizacion_id` nullable en las dos tablas y en la resolución de módulos.
```

##### Prompt MT.6 (RED/GREEN) — Los prompts de actividad, heredables

**Modelo sugerido**: **Sonnet** — el patrón ya está en MT.1 y el modelo es pequeño.

**Objetivo**: `HubActivityPrompt.activity` es único global. Es defendible para una actividad de
plataforma y deja de serlo en cuanto un municipio quiera su propia redacción — que es
exactamente lo que esta tabla existe para permitir, sólo que un escalón más arriba de lo que
hace falta.

```
# PROMPT MT.6 — Un municipio puede escribir su propio prompt
# Deploy: cloud

## RED
- La unicidad pasa de `activity` a `(activity, organizacion_id)`.
- `test_should_inherit_the_platform_prompt`, `test_should_override_it_per_organisation`.
- `test_should_keep_the_code_default_as_the_last_resort`: la cadena entera —organización →
  plataforma → código— sin perder lo que PRO.2.1 fijó: el texto del código no se copia.
```

##### Prompt MT.7 — El inventario del ámbito, escrito donde se lee

**Modelo sugerido**: **Sonnet** — documentación con un test detrás.

**Objetivo**: cerrar la fase con `docs/MULTITENENCIA.md`: qué está acotado, por qué camino, y
qué es deliberadamente de plataforma. Lo que hoy hay que reconstruir leyendo 31 tablas y 32
routers, que es lo que costó esta auditoría.

```
# PROMPT MT.7 — Que la próxima auditoría dure diez minutos
- Tabla por tabla: ámbito, camino hasta la organización, y router que lo aplica.
- Enlazado desde AGENTS.md, junto a la frontera edge/cloud.
- El test de MT.1 comprueba que el documento nombra todas las tablas de configuración.
```

---

#### MT fase 2 — la vista y los permisos (DESPUÉS del piloto). 9 prompts

No se detallan al nivel de los de arriba porque **dependen de cómo quede el piloto**: si la UJI
acaba con una sola organización y sin administradores delegados, la mitad de estas pantallas
cambian de forma. Se enumeran para que el alcance esté acotado y no aparezcan de sorpresa.

- **MT.8** — El selector de la cabecera **filtra** los listados de un superadministrador. Filtro
  y no permiso: seguir pudiendo verlo todo es correcto, verlo todo **a la vez** es lo que estorba.
- **MT.9** — Un administrador gestiona a las personas de su organización. Hoy `list_users` es
  sólo de superadministrador, así que un administrador no puede dar de alta a su propia gente.
- **MT.10** — Pantalla de modelos y proveedores con el nivel elegible, y la credencial de cada
  organización guardada como tal. **Aquí vive el `SecretProvider` (anotado el 2026-08-24 desde
  SEC.9.4)**: una abstracción con la misma forma que `StorageService`/fsspec —Secret Manager en
  GCP, fichero o entorno en local— para que el panel recupere el **autoservicio** que SEC.9.4 le
  quita, sin que el secreto vuelva a la base de datos: se guarda el **nombre del recurso**, no el
  valor. Es lo que evita que la fricción de dar de alta una credencial por organización empuje a
  compartir una entre varias, que es peor que las dos opciones que SEC.9.4 comparaba.
- **MT.11** — Plantillas de informe con nivel de organización en la interfaz.
- **MT.12** — Prompts (de actividad y de chatbot) con su nivel, sobre la pantalla unificada de
  REV.13.
- **MT.13** — Alta de organización **con su administrador**, que es el flujo que describe el
  usuario: el superadministrador da de alta la organización y designa quién la administra.
- **MT.14** — Concesiones por organización en la pantalla de módulos.
- **MT.15** — Cuotas por organización en la interfaz. El modelo ya las soporta desde SEC.4; falta
  poder verlas y fijarlas sin tocar la base.
- **MT.16** — **Prueba de aislamiento de punta a punta con dos organizaciones**: dos
  administradores, dos corpus, dos juegos de modelos, y la comprobación de que ninguno ve nada
  del otro. Es el prompt que cierra el bloque y el único que demuestra que lo demás sirvió.
  **Adelantado a SEC.9.7 (2026-08-24)**: es lo único que valida el aislamiento, y el piloto
  arranca con una sola organización, así que sin él el aislamiento no se ejercita en producción.
  Aquí queda como referencia; su ejecución vive en el Bloque SEC.9.

**Añadidos el 2026-08-24**, de la conversación sobre reutilizar configuración entre municipios.
Van en la fase 2 porque **todos empiezan vacíos**: no hay datos que migrar, así que esperar no
cuesta nada. Lo único de esa conversación que sí entra antes del piloto es la procedencia
(MT.4.2), porque es lo que no se puede reconstruir después.

- **MT.17** — `capacidades` en la organización y `requiere` en el artefacto de catálogo, que es
  cómo se resuelve «esto vale para todas» y «esto sólo para las que compartan G400» con un solo
  mecanismo. Comparación plana clave→valor, **no expresiones**.
- **MT.18** — **Plantilla de asistente**: el `spec` de una configuración de chatbot —prompt base,
  nivel de modelo, modo de recuperación, troceado, modo de acceso— como artefacto de catálogo, y
  la operación que lo materializa en un chatbot de una organización. **Tabla nueva y no un
  `organizacion_id` nullable en `hub_chatbots`**: un chatbot posee corpus y conversaciones, así que
  compartir la fila compartiría los datos. La copia anota su procedencia (MT.4.2).
- **MT.19** — Pantalla del catálogo: qué hay elevado, quién lo consume, qué copias se han quedado
  atrás respecto a la versión vigente.
- **MT.20** — **Exportar e importar** el `spec` de un artefacto de catálogo. No es alternativa al
  nivel de plataforma: sirve **entre instalaciones**, que es el caso de una empresa con un
  despliegue `edge` por municipio y sin base de datos común. Si MT.18 define bien el `spec`, esto
  es escribirlo a un fichero y validarlo al leerlo.
- **MT.21** — El mismo mecanismo aplicado a **automatizaciones** y **expedientes** cuando esos
  módulos existan: el script y la plantilla de procedimiento se comparten por referencia; la
  ejecución y el expediente son datos de la organización y no se comparten nunca.

### Lo que este bloque NO hace, y hay que decirlo

No convierte la instalación en multiinstancia: sigue siendo **una base de datos con
organizaciones dentro**. Si una Diputación exige separación física por municipio —cada uno su
base—, eso es el modo `edge` de la frontera que ya describe `AGENTS.md`, y es otra conversación.
Lo que este bloque garantiza es que el modelo lógico aguante, que es el requisito de hoy.
