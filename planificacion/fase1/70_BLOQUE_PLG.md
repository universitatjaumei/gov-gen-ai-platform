## Bloque PLG — Perfiles, estrategias y pipelines de recuperación descubiertos por *entry points* (PENDIENTE, planificado el 2026-09-02, ampliado el mismo día con las estrategias)

> **Posición**: independiente de Deploy, REG, DIN y FUN. Conviene ejecutarlo **después de LANG**,
> que toca la misma factoría de perfil (`_make_public_kb_rich`) para montar la política de
> lengua: dos bloques editando la misma función en paralelo es un conflicto seguro. 3 prompts.
>
> **Ampliado el 2026-09-02**: la primera versión de este bloque descubría perfiles y pipelines y
> dejaba fuera las estrategias con el argumento de que «una estrategia suelta no es seleccionable
> por configuración». El usuario señaló que **la carga de estrategias por plugin es lo que se
> aceptó con desarrollo** (el correo lo promete: «perfils i estratègies del propi nucli entren pel
> mateix mecanisme»), y el argumento se resuelve al revés: **hacer las estrategias seleccionables
> por configuración**, eje a eje, con un registro por eje y sobreescritura en la cascada. Es la
> forma literal de «una estrategia es un enchufe». Nuevo PLG.2; el panel pasa a PLG.3.
>
> **Lo que este bloque NO hace, a propósito**: congelar los protocolos de estrategia ni la firma
> de factoría como contrato público con deprecaciones. Han cambiado dos veces en un mes por
> medición (la puerta de calidad en HIB, la política de lengua en LANG) y congelarlos hoy sería
> congelar errores conocidos. Se declaran **inestables (0.x)** por escrito, y el contrato se fija
> el día que exista el primer tercero real con un perfil que mantener.

**Origen**: el correo de desarrollo del 2026-09-02 («que la carga de las distintas estrategias sea
dinámica, un sistema de plugins, es algo que puede afectar al diseño y conviene que esté previsto
de inicio aunque no esté abierto a otros desarrolladores; ahora mismo las estrategias más core
pueden ser ya plugins»). La respuesta (informe, decisión 9 revisada) fue **sí al descubrimiento,
no a la congelación**. El argumento a favor que el correo no hizo y que decide el bloque: si el
propio núcleo entra por el mismo mecanismo, el motor queda **obligado** a no depender de nada que
no pase por el registro, que es justo hacia donde ya empuja el test de contrato de perfiles.

**Estado de partida, medido**:

- `GraphProfileRegistry.register_profile()` existe y es la costura; la llama `graph_factory.py`
  al importarse, con tres perfiles (uno operativo, dos en `PERFILES_SIN_CONFIGURAR` que fallan
  en alto). `register_profile` **sobrescribe en silencio** si el nombre se repite.
- `PublicGraphProfile` es un `Enum` cerrado (`types.py`): un perfil de terceros **no cabe** por
  construcción. Contradice la regla «el vocabulario es dato»: un nombre de perfil que llega por
  instalación no puede ser miembro de un enum del núcleo.
- `retrieval_pipeline_factory.get_pipeline()` es una cadena de `if` sobre `_VALID_MODES`
  cerrada; `hub_chatbots_router.py` y `hub_organizaciones_router.py` tipan `retrieval_mode` como
  `Literal[...]` cerrado y **no validan** `public_graph_profile` contra nada (es `str` libre).
- El frontend lleva los nombres de perfil y de modo **hardcodeados** en
  `frontend/src/admin/chatbots/schemas/chatbotSchemas.ts`, `ChatbotsPage.tsx` y
  `ValoresPorDefectoPage.tsx`: viola la regla maestra de contrato (la UI no conoce las opciones
  a priori) y sería lo primero que un perfil instalado no podría atravesar.
- **El servidor no está instalado como paquete en el venv** (sólo `automatia_shared` lo está,
  en editable; `server/pyproject.toml` no declara `[build-system]`). Consecuencia: unos *entry
  points* declarados en el `pyproject.toml` del servidor **no serían visibles** para
  `importlib.metadata` hasta que el proyecto sea instalable. Es la decisión técnica del bloque
  (ver PLG.1).

**Qué construye el bloque**: tres grupos de *entry points*, `govgenai.graph_profiles` (nombre del
perfil → factoría `(cfg, deps, llm) -> CoreGraph`), `govgenai.strategies` (`<eje>.<nombre>` →
factoría `(cfg, deps, llm) -> estrategia` de ese eje) y `govgenai.retrieval_pipelines` (nombre
del modo → clase que implementa `RetrievalPipeline`); un cargador que los descubre al arrancar y
los registra **por la misma API** que el núcleo, fallando en alto ante nombres duplicados o
factorías que no cumplen el contrato; **un registro de estrategias por eje** del que el perfil
operativo toma su composición por nombre y que la cascada Plataforma → Organización → Chatbot
puede **sobreescribir eje a eje**; la validación de perfil, modo y estrategias en los routers
contra los registros y no contra literales; y el panel tomando las opciones del servidor.

**Los cuatro ejes de estrategia** son los protocolos que compone el `CoreGraph`: `retrieval`
(`RetrievalStrategy`), `merge` (`MergeStrategy`), `template` (`TemplateStrategy`) y `language`
(`LanguagePolicy`). Son **estructura**, no vocabulario: van en un `StrEnum`, porque añadir un eje
exige de todos modos un nodo que lo consuma. El bucle agéntico **no** es un eje: lo monta
`build_agentic_loop_if_needed` a partir del modo de recuperación y de sus dependencias, y
convertirlo en enchufe exigiría antes separar sus tres colaboradores (lector, buscador,
puntuador); queda anotado como candidato, no se hace aquí.

**Cómo se selecciona una estrategia**: el perfil declara una **composición por defecto**
(`PUBLIC_KB_RICH` = `retrieval:single_source`, `merge:passthrough`, `template:generic`,
`language:default`); la organización puede fijar `default_estrategias` y el chatbot
`estrategias`, ambos `JSONB` `{eje: nombre}` **heredables clave a clave** (nulo o clave ausente =
se hereda). Un chatbot de normativa que quiera una fusión distinta cambia **una clave**, sin perfil
nuevo ni código. Una estrategia aportada por un paquete es seleccionable en cuanto se instala.

**Reglas duras del bloque PLG**:

- **Un solo camino de registro.** El cargador de *entry points* y el núcleo usan la misma
  función de registro; no hay un registro «de plugins» aparte. Si al cerrar el bloque el núcleo
  puede declararse como *entry point* (PLG.1 decide), lo hace y `graph_factory.py` deja de
  registrar por código; si no puede, registra por código **a través del mismo cargador**, y la
  razón queda escrita.
- **Fallar en alto, nunca sobrescribir.** Dos *entry points* con el mismo nombre, o un nombre que
  colisiona con uno del núcleo, abortan el arranque nombrando ambas distribuciones. Una factoría
  que no produce un `CoreGraph` con las cuatro estrategias no nulas se rechaza al arrancar, no
  en la primera petición. `register_profile` deja de sobrescribir en silencio (hoy lo hace).
- **El enum se retira.** `PublicGraphProfile` desaparece como tipo cerrado; el nombre de perfil es
  una cadena validada contra el registro. `PERFILES_SIN_CONFIGURAR` se conserva como conjunto de
  cadenas y sigue significando lo mismo. Sin shims ni re-exports (regla del proyecto).
- **Sin sandbox, y se dice.** Un perfil o pipeline instalado corre en el proceso del servidor con
  los datos del cliente. La confianza está en quien instala, como en cualquier plugin de pytest o
  Airflow, y así lo dice `docs/GRAPH_PROFILES.md`. No se finge otra cosa.
- **El test de contrato cubre lo instalado.** La parametrización de
  `test_profile_contract.py` sale de `list_profiles()` **después** del descubrimiento, así que un
  perfil instalado en el entorno de tests que no compile pone la suite en rojo. Lo que no está
  instalado en CI no lo cubre nadie, y eso también se escribe.
- **La UI no conoce las opciones.** Perfiles, modos y estrategias por eje llegan del servidor;
  ningún literal en React ni en el esquema zod (regla maestra 1).
- **Una estrategia se valida contra el protocolo de su eje, al arrancar y no en la primera
  petición.** Los cuatro protocolos pasan a `@runtime_checkable`; el cargador instancia cada
  estrategia descubierta con una configuración mínima y comprueba `isinstance` contra el
  protocolo del eje que declara. Una estrategia registrada en el eje equivocado aborta el
  arranque nombrando la distribución.
- **La sobreescritura se aplica en un solo sitio**: `GraphFactory.build`, la misma capa donde
  ya se resuelven el modelo de reescritura y el bucle agéntico. Las factorías de perfil no saben
  de sobreescrituras; el `CoreGraph` tampoco. Y **queda en la traza**: la configuración resuelta
  ya viaja por valor a `interaction_metadata` (HIB.I) y a la instantánea de depuración, así que
  qué estrategia corrió en cada respuesta se lee ahí sin añadir nada.

---

### Prompt PLG.1 (RED/GREEN) — El registro descubre por *entry points* y el núcleo entra por ahí

**Modelo sugerido**: **Opus** — retira un enum del núcleo, cambia la validación de dos routers y
decide sobre el empaquetado del servidor; tres cosas con efectos cruzados.

**Objetivo**: que un paquete Python instalado pueda aportar un perfil de grafo o un pipeline de
recuperación sin tocar el repositorio, y que el núcleo entre por el mismo camino.

**Instrucciones al agente**:
```markdown
# PROMPT PLG.1 (RED/GREEN) — entry points govgenai.graph_profiles y govgenai.retrieval_pipelines

## 0. La decisión de empaquetado, medida antes de escribir código
- Comprobar qué cuesta que `server/` sea instalable: añadir `[build-system]` (hatchling o el
  backend que ya use automatia_shared, por coherencia) a server/pyproject.toml, `uv lock`,
  `uv sync --locked`, y que la suite y el arranque sigan igual. Si cuesta eso y nada más ->
  el núcleo declara sus entry points en server/pyproject.toml y graph_factory.py deja de
  registrar por código. Si rompe algo que no se arregla en el prompt (CI, Docker, el
  --extra local-models) -> el núcleo registra por código a través del cargador (regla
  «un solo camino»), y la razón va en docs/GRAPH_PROFILES.md y en HISTORIAL como
  desviación documentada. No interrumpir por esto: es exactamente el caso de «desviación
  entre el plan y el código real».
- En cualquiera de los dos casos, `uv lock` va en el mismo commit (regla del proyecto).

## 1. El cargador (agent/public_graphs/plugins.py o nombre equivalente, Deploy: edge)
- descubrir_perfiles(): itera importlib.metadata.entry_points(group="govgenai.graph_profiles");
  para cada uno: cargar, comprobar que es callable, registrar con register_profile(nombre,
  factoría). Nombre = entry point name. Duplicado (con otro entry point o con el núcleo) ->
  RuntimeError que nombra las dos distribuciones. Error de import -> RuntimeError que nombra
  la distribución; nunca warning-y-seguir.
- descubrir_pipelines(): igual sobre "govgenai.retrieval_pipelines"; el objeto cargado debe
  cumplir RetrievalPipeline (runtime_checkable) o se rechaza.
- Se invoca UNA vez en el lifespan de la app y en el conftest de tests (misma función). PLG.2
  añade descubrir_estrategias() al mismo cargador; dejar el punto de extensión (una lista de
  descubridores, no tres llamadas sueltas).

## 2. Los registros
- GraphProfileRegistry.register_profile(nombre: str, factoría): nombre es str, no enum;
  registrar dos veces el mismo nombre -> ValueError (hoy sobrescribe).
- retrieval_pipeline_factory: de cadena de `if` a registro (dict nombre -> clase) con
  register_pipeline()/get_pipeline()/list_modes(); los tres modos del núcleo se registran por
  el mismo camino. get_pipeline con modo desconocido -> el mismo ValueError de hoy, con la
  lista de disponibles.
- Retirar PublicGraphProfile (types.py) y todos sus usos: grep -r a cero. Los nombres son
  cadenas; PERFILES_SIN_CONFIGURAR pasa a frozenset[str].

## 3. Validación en los routers (hub_chatbots_router, hub_organizaciones_router)
- public_graph_profile y retrieval_mode (y sus default_* en organización) se validan contra
  list_profiles()/list_modes() en el servicio, con 422 tipado que lista las opciones. Los
  Literal[...] cerrados de los DTO se retiran: el contrato OpenAPI expone `str` y la lista
  viva llega por el endpoint de PLG.2.
- Un perfil en PERFILES_SIN_CONFIGURAR sigue rechazándose al crear/editar como hasta ahora.

## 4. Verificación de arranque
- Tras descubrir, por cada perfil registrado y no en PERFILES_SIN_CONFIGURAR: construir el
  grafo con una PublicGraphConfig mínima y deps nulas y comprobar que devuelve CoreGraph con
  las cuatro estrategias no nulas. Falla -> el arranque falla nombrando perfil y
  distribución. Es lo que hoy hace test_profile_contract, llevado al arranque para lo
  instalado.

## 5. Fixture de pruebas
- tests/fixtures/paquete_perfil_demo/: pyproject con un entry point en cada grupo (un perfil
  que envuelve las estrategias de PUBLIC_KB_RICH con otro nombre; un pipeline trivial que
  devuelve un RetrievalResult fijo). Instalado en editable en el entorno de tests, o
  simulado vía importlib.metadata si instalar resulta frágil: decidirlo midiendo y
  documentarlo (mismo criterio que FUN.5; si FUN.5 ya decidió, reutilizar su decisión).

## 6. Documentación
- docs/GRAPH_PROFILES.md: sección «Aportar un perfil o un pipeline desde un paquete»
  (descriptor, grupos, qué valida el arranque, colisiones), sección «Estabilidad: los
  protocolos de estrategia, RetrievalPipeline y la firma de factoría son 0.x» (pueden
  cambiar entre versiones menores; se anuncia en HISTORIAL; sin política de deprecación
  hasta el primer tercero), y la frontera de confianza dicha sin rodeos (in-process; quien
  instala responde). Actualizar los pasos «Cómo añadir un perfil/pipeline nuevo» (ya no se
  toca el enum).

## Tests (mínimo 10) — server/tests/public_graphs/test_plg1_entry_points.py
- El paquete demo aporta un perfil: aparece en list_profiles() y construye un CoreGraph.
- El paquete demo aporta un pipeline: aparece en list_modes() y get_pipeline lo devuelve.
- Entry point con nombre duplicado -> RuntimeError que nombra ambas distribuciones.
- Entry point cuyo import falla -> RuntimeError que nombra la distribución (no warning).
- Pipeline que no cumple el protocolo -> rechazado al descubrir.
- register_profile dos veces el mismo nombre -> ValueError.
- Crear un chatbot con perfil inexistente -> 422 que lista los disponibles; con el del
  paquete demo -> 201.
- retrieval_mode inexistente -> 422; el del paquete demo -> 201.
- Perfil de PERFILES_SIN_CONFIGURAR -> rechazado igual que antes (regresión).
- grep del árbol: PublicGraphProfile a cero (test de higiene, mismo patrón que los de
  test_suite_hygiene).
- test_profile_contract.py parametriza desde list_profiles() tras el descubrimiento e
  incluye el perfil del paquete demo (comprobar que el id aparece en la colección).
```

**Verificación**: `server/tests/public_graphs/` + `tests/modules/agents_hub/unit/` + higiene
verdes; arranque real del servidor con el paquete demo instalado y el log de descubrimiento
visible; `uv lock --check` limpio; `grep -r PublicGraphProfile` a cero.

---

### Prompt PLG.2 (RED/GREEN) — Estrategias por eje: registro, *entry points* y sobreescritura en la cascada

**Modelo sugerido**: **Opus** — convierte la composición fija de un perfil en composición por
nombre, añade una columna heredable a dos tablas con migración, y decide cómo convive con la
política de lengua de LANG; tres cosas con efectos cruzados y una regresión fácil de introducir
(que el perfil operativo deje de montar exactamente lo que montaba).

**Objetivo**: que una estrategia (de recuperación, fusión, plantilla o lengua) aportada por un
paquete instalado sea seleccionable por configuración para un chatbot o una organización, sin
perfil nuevo ni código, y que el núcleo registre las suyas por el mismo camino.

**Instrucciones al agente**:
```markdown
# PROMPT PLG.2 (RED/GREEN) — govgenai.strategies + sobreescritura por eje. Deploy: edge (registro y
# factoría) · cloud (columnas y validación en routers)

## 1. Ejes y protocolos
- EjeDeEstrategia (StrEnum): retrieval | merge | template | language. Estructura, no
  vocabulario (regla del proyecto): añadir un eje exige un nodo que lo consuma.
- Los cuatro Protocol de strategies/protocols.py pasan a @runtime_checkable. Comprobar que
  isinstance funciona con las implementaciones actuales (métodos con firma, sin atributos
  de datos que rompan la comprobación estructural).

## 2. El registro (agent/public_graphs/strategies/registry.py, o junto al de perfiles)
- StrategyRegistry: register_strategy(eje, nombre, factoría: (cfg, deps, llm) -> instancia),
  get_strategy(eje, nombre), list_strategies(eje) -> [nombre]. Nombre repetido en el mismo
  eje -> ValueError (nunca sobrescribir). Eje inválido -> ValueError.
- El núcleo registra las suyas por el mismo camino, en el import de graph_factory como hoy
  los perfiles: retrieval:single_source, merge:passthrough, template:generic,
  language:default. Si LANG ya cerró, sus políticas (none, fixed) se registran en el eje
  language con sus nombres y language_mode sigue seleccionando la política POR DEFECTO del
  perfil; una sobreescritura explícita del eje language manda sobre language_mode, y el DTO
  lo dice (test).

## 3. Descubrimiento (el cargador de PLG.1 gana descubrir_estrategias)
- Grupo "govgenai.strategies"; nombre del entry point "<eje>.<nombre>" (p. ej.
  merge.dedup_por_documento). Eje fuera del StrEnum -> RuntimeError que nombra la
  distribución. Duplicado -> RuntimeError que nombra ambas distribuciones.
- Verificación al arrancar (misma pasada que la de perfiles de PLG.1 §4): instanciar cada
  estrategia descubierta con PublicGraphConfig mínima y deps nulas y comprobar isinstance
  contra el protocolo de su eje; si no cumple -> el arranque falla nombrando estrategia y
  distribución.

## 4. El perfil operativo compone por nombre
- _make_public_kb_rich deja de importar las cuatro clases y resuelve su composición por
  defecto desde el registro (dict eje -> nombre). Las clases no se mueven ni se renombran.
  Test de regresión: sin sobreescrituras, el CoreGraph resultante tiene EXACTAMENTE las
  mismas clases de estrategia que antes del prompt (comparar type() de las cuatro).
- Los perfiles de PERFILES_SIN_CONFIGURAR no se tocan.

## 5. La sobreescritura en la cascada
- Columnas nuevas: HubOrganizacion.default_estrategias JSONB nullable y
  HubChatbot.estrategias JSONB nullable, forma {eje: nombre}. Migración Alembic aplicada.
  docs/MULTITENENCIA.md actualizado (su test lo exige): ámbito heredable, clave a clave.
- PublicGraphConfig.estrategias: dict[str, str] resuelto en config_resolver: composición por
  defecto del perfil <- default_estrategias de la organización <- estrategias del chatbot,
  fusión CLAVE A CLAVE (una organización que fija merge no pisa el template del chatbot).
  Nulo o clave ausente = hereda. El resultado siempre trae los cuatro ejes.
- GraphFactory.build: tras construir el grafo con la factoría del perfil, por cada eje cuyo
  nombre resuelto difiera del que montó el perfil, instanciar por el registro y asignar el
  atributo correspondiente del CoreGraph (retrieval_strategy, merge_strategy,
  template_strategy, language_policy) ANTES de compilar. Misma capa que rewrite_llm y
  agentic_loop; ni las factorías de perfil ni CoreGraph saben de sobreescrituras.
- Nombre no registrado en tiempo de build -> RuntimeError que nombra eje, nombre y chatbot
  (nunca caer al defecto en silencio: la lección de los perfiles sin configurar).

## 6. Validación en los routers (hub_chatbots_router, hub_organizaciones_router)
- estrategias / default_estrategias: cada clave es un eje del StrEnum y cada valor está en
  list_strategies(eje); si no -> 422 que lista los ejes y, para el eje fallido, los nombres
  disponibles. Los DTO exponen el dict tal cual y el resuelto (efectivo) en el DTO de lectura
  del chatbot, para que el panel enseñe qué corre de verdad.

## 7. Traza
- Comprobar (test) que interaction_metadata (HIB.I) y la instantánea de depuración
  (resolved_config) incluyen `estrategias` resuelto: llega por valor con el resto de la
  configuración. Si el snapshot de claves de la traza está fijado por test, actualizarlo a
  conciencia (es el aviso de HIB.I: un cambio de claves rompe el instrumental en silencio).

## 8. Fixture
- El paquete demo de PLG.1 gana dos entry points en govgenai.strategies: una merge que
  deduplica por documento y una template que antepone una cabecera fija (ambas triviales y
  observables en la salida).

## 9. Documentación
- docs/GRAPH_PROFILES.md: sección «Estrategias: los cuatro ejes, cómo registrar una, cómo
  seleccionarla por configuración», y la nota de que el bucle agéntico no es eje y por qué.

## Tests (mínimo 12) — server/tests/public_graphs/test_plg2_estrategias.py
- Regresión: PUBLIC_KB_RICH sin sobreescrituras monta las mismas cuatro clases de antes.
- El paquete demo registra sus dos estrategias; aparecen en list_strategies del eje.
- Chatbot con estrategias={"merge": "dedup_por_documento"} -> el CoreGraph construido lleva
  esa clase en merge_strategy y las otras tres del perfil.
- Organización con default_estrategias={"template": ...} y chatbot con estrategias={"merge":
  ...} -> el resuelto lleva ambas (fusión clave a clave); chatbot con la misma clave que la
  organización -> gana el chatbot.
- Eje desconocido en el cuerpo -> 422 con los ejes; nombre desconocido -> 422 con los nombres
  del eje.
- Estrategia registrada en el eje equivocado (fixture ad hoc) -> el arranque falla nombrándola.
- Nombre duplicado en el mismo eje -> ValueError / RuntimeError según la vía.
- Nombre que desaparece (paquete desinstalado) con un chatbot que lo referencia -> el build
  falla en alto nombrando eje, nombre y chatbot; no cae al defecto.
- La traza de una interacción y la instantánea de depuración incluyen `estrategias`.
- Si LANG ya cerró: sobreescritura explícita de language manda sobre language_mode y el DTO
  lo indica.
- test_profile_contract.py: por cada estrategia registrada en cada eje, PUBLIC_KB_RICH con
  esa única sobreescritura compila y ejecuta el smoke (parametrizado desde el registro tras el
  descubrimiento).
- Higiene: ninguna de las cuatro clases del núcleo se importa directamente desde
  graph_factory (grep en test).
```

**Verificación**: suite de `server/tests/public_graphs/` + `tests/modules/agents_hub/unit/` +
higiene verdes; `alembic current` con la revisión; arranque real con el paquete demo y un chatbot
configurado con su merge: la respuesta por API muestra el efecto y la traza lo registra;
`docs/MULTITENENCIA.md` actualizado.

---

### Prompt PLG.3 (RED/GREEN) — El panel toma perfiles, modos y estrategias del servidor

**Modelo sugerido**: **Sonnet** — endpoint de lectura y sustitución de literales por datos del
contrato; alcance cerrado.

**Objetivo**: que un perfil, modo o estrategia aportados por un paquete sean seleccionables desde
el panel sin tocar el frontend, y que desaparezcan los literales hardcodeados.

**Instrucciones al agente**:
```markdown
# PROMPT PLG.3 (RED/GREEN) — opciones de grafo desde el servidor. Deploy: cloud

## Backend
- GET /api/v1/hub/chatbots/opciones-de-grafo (nombre a criterio, coherente con el router):
  {perfiles: [{nombre, configurable: bool, descripcion?, composicion: {eje: nombre}}],
  modos: [{nombre, descripcion?}], estrategias: {eje: [{nombre, descripcion?, origen:
  nucleo|paquete, distribucion?}]}}.
  `configurable` = no está en PERFILES_SIN_CONFIGURAR. La descripción sale de la docstring
  de la factoría/pipeline/estrategia si existe (primera línea), y es opcional: no se inventa
  i18n para nombres de terceros.
- Acotado a admin/superadmin como el resto del router de chatbots.

## Frontend
- ChatbotsPage, ValoresPorDefectoPage y chatbotSchemas.ts dejan de conocer PUBLIC_KB_RICH,
  RAG, MD_LONG_CONTEXT, MD_AGENT_SELECTOR: los selects se rellenan del endpoint; el esquema
  zod valida `string` no vacío y la validación de pertenencia es del servidor (422 mostrado
  tal cual). Los perfiles con configurable=false se muestran deshabilitados con su motivo.
- Sección «Estrategias» en el formulario del chatbot y en los valores por defecto de la
  organización: un select por eje, con la opción «heredar» (= clave ausente) por defecto y el
  valor efectivo mostrado al lado (del DTO resuelto). Los ejes salen de la respuesta, no de
  una lista en React.
- Orval regenerado. i18n es/ca/en para las etiquetas de la pantalla (no para los nombres).
- grep -r de los cuatro literales en frontend/src (fuera de generated y de tests que los
  usen como datos de fixture) a cero.

## Tests (mínimo 7)
- El endpoint lista los perfiles, modos y estrategias registrados, incluidos los del paquete
  demo si está instalado en el entorno de tests.
- configurable=false para PERFILES_SIN_CONFIGURAR.
- Frontend: los selects se generan desde la respuesta (test con MSW/mocks del hook), no desde
  literales; un perfil no configurable aparece deshabilitado.
- Frontend: los selects de estrategias se generan por eje desde la respuesta; «heredar»
  envía la clave ausente, no una cadena vacía.
- Frontend: el valor efectivo mostrado es el del DTO resuelto.
- Frontend: el 422 del servidor se muestra como error del campo.
- Higiene frontend: ningún literal de perfil/modo/eje en src/ fuera de generated.
```

**Verificación**: navegador — crear un chatbot eligiendo el perfil del paquete demo y la merge del
paquete demo en su eje, comprobar que se guarda, que el efectivo se muestra y que responde;
`read_console_messages` y `read_network_requests` limpios. Suite frontend con
`--no-file-parallelism` verde.

**Al cerrar el bloque**: suite completa desde Git Bash; informe con la decisión de empaquetado
tomada en PLG.1 y su razón; `.bat` humano previsiblemente innecesario (todo verificable en
navegador).

---
