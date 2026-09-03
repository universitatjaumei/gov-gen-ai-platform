## Bloque PRO — Las puertas al LLM del módulo de Informes, con el legacy delante

> **Planificado el 2026-08-17**, al cerrar el Bloque VER, y **reescrito el mismo día** cuando el
> usuario avisó de que todo esto ya estaba programado, probado y funcionando en la aplicación
> NiceGUI, que vive completa en `C:\Users\fabra\Documents\AutomatIA`.
>
> Ese aviso cambia el bloque de arriba abajo. Lo que iba a ser «cablear dos dependencias y
> pelearse con un auditor» pasa a ser **portar decisiones ya tomadas y probadas**, y varias son
> mejores que las del código nuevo.

### Lo que el legacy tiene y aquí falta o está peor

Leído en `AutomatIA/` el 2026-08-17. No hay que volver a buscarlo:

| Pieza del legacy | Qué resuelve | Estado en la aplicación nueva |
|---|---|---|
| `automatia_shared/core/security.py` → `audit_code()` | Auditoría **determinista** con tres niveles: `SAFE` / `WARNING` / `CRITICAL`, con motivos y nodos bloqueados. Antes del AST, **regex de rutas absolutas** —`C:\`, `C:/`, `/home`, `/etc`, `/usr`, `/var`, `/root`, `/tmp`, `/proc`, `/sys`— que fallan rápido | `ScriptSecurityAuditor` es **binario** (`approved = not findings`) y **no comprueba rutas absolutas**. Un script que abra `C:\Users\...` pasa su auditoría |
| `services/external_script_audit_service.py` | Auditoría de scripts **traídos de fuera**: cuatro severidades (INFO/WARNING/CRITICAL/BLOCKED), **número de línea** por hallazgo, y la distinción clave `is_safe` vs `can_proceed_with_review` («warnings pero ningún blocked») | No existe |
| `modules/factory/etl_factory.py` (369 l.) + `services/etl_service.py` (424 l.) | Orquestador ETL completo: leer fichero → generar script con IA → **auditar** → ejecutar en sandbox | `services/transformation/etl_factory.py` existe, pero **el nodo ETL del grafo se construye sin modelo** —VER.1 no le pasó `etl_llm`— y **no hay ningún endpoint de ETL** en el contrato |
| `services/deterministic_etl_service.py` (350 l.) | Transformaciones pandas **sin IA**: quitar y renombrar columnas, fusionar, etc. | El modo `deterministic` existe en el contrato de bloque; conviene comparar el catálogo de operaciones antes de dar por bueno el nuevo |
| `models/chart_configuration.py` (198 l.) | Gráficos **deterministas** sin IA, configurados por Pydantic | `services/charts/chart_factory.py` y los dos endpoints de preview existen y **no tienen stub**: es la pieza más avanzada de las cuatro |
| `services/extraction_service.py` (163 KB) | Extracción determinista de PDF — **el módulo más probado del legacy**, según el usuario | `pdf_text_pipeline` + `pdf_table_pipeline`, que en VER.4 extrajeron bien un Excel real. Comparar antes de tocar |
| `ui/focus_manager.py`, `ui/components/drawer_hub.py`, `side_drawer.py`, `copilot_chat.py`, `step_panels/copilot_panel.py`, `services/copilot_context_service.py` (42 KB) | El copiloto **en el drawer** y el **modo foco**, con su servicio de contexto | `CopilotPanel` → `DrawerHub` → `FocusLayout` existen en React y **`FocusLayout` no lo monta ninguna ruta**. No hay que decidir dónde va: hay que mirar cómo estaba |
| `services/script_ingestion_service.py` + `script_adaptation_service.py` | Scripts **libres**: subir uno de fuera, analizarlo y **adaptarlo** al contrato de la plataforma (`adapt_to_platform`, `adapt_from_template`, `_adapt_with_ai`) | No existe. **Decisión: va al bloque de automatizaciones, no aquí** — razonado abajo |

### Las cuatro decisiones de este bloque

1. **La auditoría deja de ser binaria y recupera los tres niveles del legacy.** Hoy
   `approved = not findings`: un `import csv` tumba la propuesta igual que un `eval()`. Con
   `SAFE` / `WARNING` / `CRITICAL`, un módulo fuera de la lista blanca es un warning que un
   administrador puede aceptar mirándolo, y `eval()` sigue siendo un no. **Y se recupera la
   comprobación de rutas absolutas**, que la nueva perdió: un script de informe sólo puede
   leer el fichero que la plataforma le pasa en `file_path`.

2. **Dos modelos, dos niveles, como pidió el usuario**: **Tier 2 para escribir** el script
   —tarea de lógica— y **Tier 3, superior, para auditar**. Hoy **todas las configuraciones
   de LLM son de nivel 1**, así que hay que crearlas; `get_model_for_tier` ya acepta cualquier
   nivel. La auditoría con modelo va **encima** de la determinista, nunca en su lugar: la
   determinista es la que no se puede convencer.

3. **Se compara con el legacy antes de escribir.** En ETL y en extracción de PDF el legacy
   está más probado que el código nuevo, y el usuario avisa de que ETL y gráficos son lo que
   más se va a usar en los informes. Cada prompt de esos empieza leyendo el fichero del legacy
   y anotando qué falta, no suponiendo.

4. **El copiloto se monta como estaba**, no donde nos parezca. `focus_manager.py` y
   `drawer_hub.py` dicen cómo se abría y con qué contexto.

### Por qué los scripts libres van a automatizaciones y no aquí

El propio legacy da la respuesta, y es más limpia que cualquier argumento nuestro: tenía **dos
auditorías distintas** porque el modelo de confianza es distinto.

- `audit_code()` es para código que **la plataforma misma generó**: tres niveles, y en el flujo
  de factoría un `WARNING` no se ejecuta («Si es WARNING, NO EJECUTES», dice el comentario).
- `ExternalScriptAuditService` es para código que **trajo una persona de fuera**: cuatro
  severidades y `can_proceed_with_review`, porque ahí sí hace falta que un humano pueda
  aceptar un warning con nombre y apellidos.

En un informe, un script tiene un trabajo estrecho y comprobable por máquina: asignar `result`
con `tables`/`metrics`/`free_text` y correr en el sandbox contra un documento que alguien acaba
de subir. Cualquier código que cumpla eso **ya puede entrar hoy** por la cola de aprobación que
VER.5 dejó funcionando. Un formulario de subida añadiría una puerta, no una capacidad.

Lo que `script_adaptation_service` aporta —analizar un script cualquiera y adaptarlo al
contrato— sólo se paga cuando lo que llega **es** cualquier cosa: RPA, vigilancia de carpetas,
integraciones con el ERP. Eso es automatizaciones. Y el riesgo también es de allí: un script de
informe lee un fichero; uno de automatización toca sistemas externos.

**Conclusión**: aquí entra la mitad valiosa —la auditoría graduada— y la ingesta y adaptación
de scripts externos se planifica con el bloque de automatizaciones, donde su auditoría de
cuatro niveles tiene sentido.

### Prerrequisitos

Los del Bloque VER, ya resueltos, más el sandbox con puerto publicado para el ciclo completo
(`docker run -d --rm -p 5099:5000 govgenai-prod-script-sandbox`). El legacy es **sólo lectura**:
se lee de `C:\Users\fabra\Documents\AutomatIA`, no se importa nada de allí.

> **Si prefieres un bloque más corto**: PRO.1–PRO.3 ya dejan la generación de scripts
> funcionando con la auditoría buena. PRO.4 y PRO.5 (ETL y gráficos) son los que el usuario
> señala como más usados, y PRO.6 el copiloto; se pueden partir en un bloque aparte sin que
> nada quede a medias.

---

### Prompt PRO.1 (RED/GREEN) — La auditoría recupera sus niveles y sus rutas

**Modelo sugerido**: **Opus** — decide qué es bloqueante y qué es revisable, y equivocarse por
exceso hace el módulo inusable y por defecto lo hace peligroso.

```
# PROMPT PRO.1 (RED/GREEN) — Auditoria determinista con tres niveles, portada del legacy
# Deploy: edge (modules/redaccion/services/script_auditor.py)

## Por que
`ScriptSecurityAuditor` pone `approved = not findings`: una ADVERTENCIA de modulo fuera de la
lista blanca deja la propuesta sin aprobar exactamente igual que un `eval()`. Con eso, el
modelo escribira scripts razonables que nadie puede aprobar, y el administrador no tendra
forma de distinguir un problema de seguridad de un hueco en una lista.

El legacy ya lo tenia resuelto: `automatia_shared/core/security.py:audit_code()` devuelve
`SAFE` / `WARNING` / `CRITICAL` con motivos, y **antes del AST** comprueba por regex rutas
absolutas de Windows y de sistema Linux. Esa comprobacion la aplicacion nueva **no la tiene**:
un script que abra `C:\Users\...` pasa su auditoria.

## Que hacer
1. Leer `AutomatIA/shared/automatia_shared/core/security.py` y anotar en el prompt de cierre
   que se porto y que se dejo fuera.
2. RED: un script con `import csv` es `WARNING` y **se puede aprobar con revision humana**;
   uno con `eval()` es `CRITICAL` y no; uno que abra `C:\Users\x\datos.xlsx` es `CRITICAL`
   aunque no use ninguna llamada prohibida.
3. GREEN: `AuditResult` gana `risk_level` con los tres niveles y un `puede_revisarse` —el
   `can_proceed_with_review` del legacy— y cada hallazgo lleva **numero de linea**, que es lo
   que convierte «hay un problema» en «esta en la linea 14».
4. Los llamadores actuales se adaptan: `approved` sigue significando «sin hallazgos», y quien
   decide si algo puede pasar a revision mira `puede_revisarse`.

## Restricciones
- **La lista blanca no se toca en este prompt.** Si al probar aparece un modulo que de verdad
  hace falta, se anade en PRO.2 con su razon escrita, no para desatascar una prueba.
- Nada de importar codigo del legacy: se lee y se porta con tests propios.

## Criterio de done
- [ ] Los tres niveles, con rutas absolutas cazadas
- [ ] Numero de linea en cada hallazgo
- [ ] La cola de aprobacion sigue verde de punta a punta (el ciclo de VER.5)
```

---

### Prompt PRO.2 (RED/GREEN) — Dos niveles de modelo: uno escribe, otro audita

**Modelo sugerido**: **Sonnet** — alcance cerrado en cuanto PRO.1 fija los niveles.

> **Ampliado el 2026-08-17, a mitad del bloque**, a peticion del usuario: «la asignacion del
> modelo por TIER se debe poder hacer desde frontend. El tipo de tier para cada actividad se
> puede preasignar en el codigo aunque en la aplicacion legacy existia una biblioteca de
> prompts desde la que se podia sobreescribir».
>
> Comprobado contra el codigo: **las dos mitades ya existen aqui**. `/hub/llm-configs` asigna
> `tier` y `is_default` por modelo desde el formulario, y `/hub/prompts` + `/hub/brain` son el
> editor del legacy ya portado —texto con `{variables}` resaltadas, chips de tier y
> `default_tier` + `override_tier` editables—. Lo que falta es la frontera:
> `hub_prompt_templates.chatbot_id` es NOT NULL, asi que la biblioteca solo ve prompts **de
> chatbot**, y los de las actividades de Informes viven en Python.
>
> Consecuencia para este prompt: el mapa actividad->tier **no se escribe como literales
> sueltos** en el router, sino como **catalogo en codigo**, que es lo que PRO.2.1 podra
> sobreescribir. Es la forma del legacy: `DEFAULT_TIER_MAPPING` en codigo y `tier_override`
> en base de datos.

```
# PROMPT PRO.2 (RED/GREEN) — Tier 2 escribe, Tier 3 audita
# Deploy: edge (routers/redaccion/scripts_router.py) + configuracion

## Por que
Escribir codigo y juzgar si es peligroso son tareas distintas, y el usuario pide modelos
distintos: **Tier 2 para programar** y **Tier 3, superior, para auditar**. Hoy **todas las
configuraciones de LLM son de nivel 1**, asi que el nivel existe en el codigo y no en los
datos.

## Que hacer
1. RED: test que exige que el servicio de propuesta se construya con el modelo de **nivel 2**
   y el de auditoria con el de **nivel 3**, y que si falta uno de los dos el 503 diga **cual**.
2. GREEN: `get_script_proposal_service` cableado a `model_factory`, con los dos niveles.
3. GREEN: la auditoria con modelo va **encima** de la determinista de PRO.1, no en su lugar:
   primero el AST, que no se puede convencer; despues el modelo, que explica.
4. Crear las configuraciones de nivel 2 y 3 en la base de desarrollo y **documentar cual es
   cual**, porque el nivel no dice nada por si mismo.
5. El prompt del sistema nombra tambien los prohibidos por forma —`getattr`, `globals`,
   `locals`, `vars`, `setattr`, `__class__`, `__dict__`— que el auditor marca como CRITICO y
   que hoy no aparecen en el prompt. Y los **modulos de denegacion explicita** que PRO.1
   separo de la lista blanca.
6. `/redaccion/scripts/wizard` entra en el menu de Informes: existe desde 9R y solo se llega
   escribiendo la URL.
7. El mapa **actividad -> tier por defecto** es un **catalogo en codigo** en un solo sitio,
   no un `2` y un `3` escritos en la raiz de composicion. Sin eso, PRO.2.1 no tiene nada que
   sobreescribir y el usuario no puede ver que actividades hay.

## Criterio de done
- [ ] Una peticion real produce un script que la auditoria acepta
- [ ] En navegador: describir -> proponer -> sandbox -> revision -> aprobar
- [ ] Sin nivel 2 o sin nivel 3, el 503 dice cual falta
- [ ] En navegador: asignar un modelo al nivel 2 y al 3 desde `/hub/llm-configs`
```

---

### Prompt PRO.2.1 (RED/GREEN + navegador) — La biblioteca de prompts llega a las actividades

**Modelo sugerido**: **Opus** — decide donde vive la configuracion de una actividad de
plataforma sin romper la frontera edge/cloud ni la tabla que ya sirve a los chatbots.

```
# PROMPT PRO.2.1 (RED/GREEN) — Actividad, prompt y tier: preasignado en codigo, sobreescribible
# Deploy: shared (modelo de configuracion) + edge (quien lo consume)

## Por que
Los prompts de las actividades del modulo —generar un script, auditarlo con modelo, ETL,
graficos, proponer una plantilla, redactar un bloque, copiloto— estan **escritos en Python**.
Eso significa dos cosas malas a la vez: nadie puede afinar el texto sin desplegar, y nadie
puede decidir con **que nivel de modelo** corre cada actividad, que es justo lo que PRO.2
acaba de hacer relevante.

El legacy lo tenia resuelto y el usuario pide replicarlo:
`AutomatIA/server/app/database/models.py:SystemPrompt` (name / version / content /
context_type / **tier**) y `server/app/ui/admin_prompts.py`, un editor con buscador, filtros
por tarea y fase, **radio de tier con cuatro opciones** —«por defecto (usa Tier N)», 1, 2, 3—
y las variables `{...}` detectadas en vivo. El defecto por tarea (`DEFAULT_TIER_MAPPING`)
estaba **en codigo**; la base de datos solo guardaba el override.

Y aqui esta casi todo hecho: `/hub/llm-configs` asigna modelo por tier, y `/hub/prompts` +
`/hub/brain` ya son ese editor sobre `hub_prompt_templates`, que **ya tiene `default_tier` y
`override_tier`**. Lo que no encaja es la clave: `chatbot_id` es NOT NULL, asi que una
actividad de plataforma no cabe en esa tabla.

## Que leer antes de escribir
`AutomatIA/server/app/database/seeds_prompts.py` (579 l.) y `server/app/ui/admin_prompts.py`
(295 l.). Del primero interesa la forma de la entrada —nombre estable, version, contenido,
tier opcional, activo— y del segundo que el defecto vive en codigo y la pantalla lo **dice**
(«Por defecto: Tier 2»), en vez de dejar un hueco que nadie sabe interpretar.

## Que hacer
1. RED: una actividad **sin fila en base de datos** resuelve al prompt y al tier del catalogo
   de codigo; con fila y `override_tier`, resuelve al override; con fila y texto vacio,
   resuelve al texto del codigo y al tier del override. El texto del codigo es la fuente de
   verdad de **que actividades existen**: la base de datos solo sobreescribe.
2. GREEN: modelo de configuracion propio para la actividad —**no** reutilizar
   `hub_prompt_templates` haciendo `chatbot_id` nullable: en Postgres una restriccion unica
   con NULL no colisiona, asi que la clave dejaria de ser unica justo para las filas nuevas, y
   la pantalla que filtra por chatbot dejaria de tener sentido—. Va en `HubConfigBase`
   (configuracion, se sincroniza cloud->edge) y se lee por `ConfigProvider`, como manda la
   frontera.
3. GREEN: migracion aplicada, y las actividades del catalogo **no se siembran**: existir en
   codigo ya es existir.
4. GREEN: quien consume —`ScriptProposalService`, la auditoria con modelo, `ETLFactory`,
   `ChartFactory`, `LLMSpecService`, `RedactorDeBloques`— pide su prompt y su tier al
   resolvedor en vez de llevarlos dentro.
5. GREEN: superficie y pantalla. La biblioteca que ya existe gana la vista de actividades,
   con el tier efectivo visible y de donde viene (codigo u override), las variables detectadas
   y el aviso de que un texto vacio significa «usa el del codigo».
6. Verificar en navegador: cambiar el tier de «generar script» de 2 a 3 y comprobar que la
   siguiente propuesta la escribe el modelo del nivel 3.

## Restricciones
- **Una actividad no puede inventarse desde la pantalla.** Si no esta en el catalogo de
  codigo, no hay nada que la consuma: seria configuracion muerta que parece funcionar.
- El texto por defecto **no se copia** a la base de datos al abrir la pantalla. Copiarlo
  congela el prompt: a partir de ahi, mejorarlo en el codigo no llega a quien ya lo abrio.
- Sin variables nuevas en los prompts: portar el texto tal como esta.

## Criterio de done
- [ ] Sin fila en base de datos, todo sigue funcionando igual que antes del prompt
- [ ] El tier de una actividad se cambia desde la pantalla y se nota en la peticion siguiente
- [ ] El texto de una actividad se edita desde la pantalla y llega al modelo
- [ ] La frontera edge/cloud intacta: el consumidor edge no importa modelos de configuracion
```

---

### Prompt PRO.3 (verificación en navegador) — El camino del script, de punta a punta

**Modelo sugerido**: **Sonnet**.

```
# PROMPT PRO.3 — El script propuesto por el modelo llega a un informe

## Que recorrer
Un script propuesto por el modelo tiene que acabar **extrayendo datos en un informe real**,
que es la unica prueba que importa: propuesta -> auditoria -> sandbox -> aprobacion ->
incrustado en una plantilla global -> un workspace que use esa plantilla genera con el.

## Ojo con esto
`AdminScriptExtractionPipeline` es el pipeline que ejecuta el script aprobado. Comprobar que el
`source_pipeline` del bloque determinista puede apuntar a el y que el fichero le llega por
`StorageService` —VER.4 arreglo justo eso para los otros pipelines—.

## Criterio de done
- [ ] Un informe generado con datos extraidos por un script que escribio el modelo
- [ ] Hallazgos arreglados con TDD, no listados
```

---

### Prompt PRO.4 (RED/GREEN) — ETL: el nodo del grafo tiene modelo y superficie

**Modelo sugerido**: **Opus** — es lo que el usuario señala como más usado, y hay que comparar
dos implementaciones antes de decidir.

```
# PROMPT PRO.4 (RED/GREEN) — ETL del informe, con el legacy delante
# Deploy: edge (modules/redaccion/services/transformation/, graph/nodes/data_transformation.py)

## Por que
El usuario avisa de que **ETL y graficos son lo que mas se va a usar en los informes**. Y hoy:
- `DataTransformationNode` construye `ETLService(llm=self._llm)` y **`_llm` es None**, porque
  la raiz de composicion de VER.1 no le paso `etl_llm`. El modo determinista funciona; el de
  IA, no.
- **No hay ningun endpoint de ETL** en el contrato, asi que la transformacion no se puede
  probar ni configurar sin generar un informe entero.

## Que leer antes de escribir
`AutomatIA/client_app/app/services/deterministic_etl_service.py` (350 l.) y
`services/etl_service.py` (424 l.) mas `modules/factory/etl_factory.py` (369 l.). El
orquestador legacy hace leer -> generar -> **auditar** -> sandbox; comparar el catalogo de
operaciones deterministas con el nuestro y anotar que falta.

## Que hacer
1. RED: un bloque `DATA_TRANSFORM` en modo `deterministic` transforma sin modelo; en modo `ai`
   con `etl_llm` cableado, genera, **pasa por la auditoria de PRO.1** y se ejecuta en sandbox.
2. GREEN: `etl_llm` en la raiz de composicion, con el modelo de **nivel 2** (es programar).
3. GREEN: las operaciones deterministas que el legacy tenia y aqui faltan, con sus tests.

## Restricciones
- El script de ETL pasa por el **mismo** auditor que el de extraccion. Un camino con auditoria
  y otro sin ella es no tener auditoria.

## Criterio de done
- [ ] Un informe con un bloque de transformacion que de verdad transforma
- [ ] Modo IA auditado antes de ejecutarse
- [ ] Comparativa con el legacy escrita: que se porto y que se dejo
```

---

### Prompt PRO.5 (verificación en navegador) — Gráficos en el informe

**Modelo sugerido**: **Sonnet**.

```
# PROMPT PRO.5 — Graficos deterministas y por script, dentro del informe

## Contexto
Es la pieza mas avanzada: `chart_factory` y los dos endpoints de preview
(`/charts/preview/deterministic` y `/charts/preview/script`) existen y **no tienen stub**. Lo
que falta es comprobar que un bloque `CHART` de una plantilla llega al informe ensamblado con
su imagen, no solo que el preview responda.

## Que leer antes
`AutomatIA/client_app/app/models/chart_configuration.py` (198 l.): los tipos de grafico y su
configuracion sin IA.

## Criterio de done
- [ ] Un bloque CHART aparece en la vista previa y en la exportacion
- [ ] El modo por script pasa por el auditor
```

---

### Prompt PRO.6 (RED/GREEN + navegador) — El copiloto, como estaba

**Modelo sugerido**: **Sonnet**.

```
# PROMPT PRO.6 (RED/GREEN) — copilot/ask cableado y alcanzable
# Deploy: edge (routers/redaccion/copilot_router.py, services/copilot/)

## Por que
`CopilotService` responde sobre la documentacion interna con citas y traduce lenguaje natural
a configuracion de los asistentes. Esta inalcanzable **por los dos lados**: el endpoint da 503
y `CopilotPanel` cuelga de `FocusLayout`, que **no lo monta ninguna ruta**.

## Que leer antes
En el legacy estaba montado y funcionando: `AutomatIA/client_app/app/ui/focus_manager.py`,
`ui/components/drawer_hub.py`, `side_drawer.py`, `copilot_chat.py`,
`ui/components/step_panels/copilot_panel.py` y `services/copilot_context_service.py` (42 KB).
**No hay que decidir donde se monta ni con que contexto: hay que mirar como estaba.**

## Lo medido
`DocsRetriever` indexa `docs/**/*.md` en memoria y sin persistir: **46 ficheros, 465 KB, ~387
fragmentos**, o sea 387 llamadas de embedding por indice.

## Que hacer
1. RED: el indice se construye **al primer uso**, no al arrancar, y la segunda pregunta no
   vuelve a indexar. Pagar 387 embeddings en cada arranque es un coste que casi nunca se
   aprovecha, y en modo edge con embeddings locales retrasa el arranque.
2. GREEN: `get_copilot_service` con modelo y servicio de embeddings, y 503 que diga **cual**
   de los dos falta.
3. GREEN: el copiloto se abre desde la interfaz, con la composicion del legacy como guia.
4. Verificar en navegador: una pregunta sobre el proyecto responde **con citas a ficheros
   reales de `docs/`**.

## Restricciones
- El indice es de la documentacion del proyecto, no del corpus normativo.
- Sin persistencia por ahora; si el uso la pide, es otro prompt.

## Criterio de done
- [ ] La primera pregunta indexa; la segunda no
- [ ] Respuesta con citas verificables
- [ ] Se abre sin escribir la URL
```

---

### Prompt PRO.7 (cierre) — Lo irreducible, el `.bat` y el informe

**Modelo sugerido**: **Sonnet**.

```
# PROMPT PRO.7 — Cierre del bloque PRO

## Que hacer
1. `docs/PRUEBAS_MANUALES.md`: lo recorrido pasa a «ya verificado». En la matriz queda lo
   irreducible de verdad: **la calidad del script que escribe el modelo sobre un documento
   real de la UJI** —juicio de quien conoce el dato— y si la respuesta del copiloto es util o
   solo correcta.
2. Ampliar `pruebas_manuales_bloqueVER.bat` en vez de crear otro guion: es el mismo modulo.
3. Escribir la **comparativa con el legacy**: que se porto de `AutomatIA`, que se dejo y por
   que. Es lo que evita que dentro de tres meses alguien vuelva a leer 163 KB de
   `extraction_service.py` para averiguar lo mismo.
4. Informe de cierre con cifras reales y desviaciones documentadas.

## Criterio de done
- [ ] `PRUEBAS_MANUALES.md` sin nada ya comprobado
- [ ] `.bat` ampliado, ANSI sin BOM verificado
- [ ] Comparativa con el legacy escrita
- [ ] Informe entregado
```

---

### Prompt PRO.8 (RED/GREEN + navegador) — Gráficos deterministas: lo usual sin programarlo

**Modelo sugerido**: **Sonnet** — alcance cerrado; las decisiones abiertas están tomadas abajo.

> **Añadido el 2026-08-17 al cerrar PRO**, a petición del usuario: «la idea de tenerlos
> preparados era que los más usuales se elegían de forma determinista sin tener que
> programarlos». Al medirlo, tiene razón y mi razón en PRO.5 estaba incompleta: juzgué «diez
> tipos que nadie ha pedido» sin comprobar **cuál es la alternativa cuando faltan**.
>
> La alternativa es generar código. `translate_nl_to_config(target_kind="chart_config")` **no
> devuelve una configuración**: llama a `chart_factory.generate_script()`. O sea que «un gráfico
> de barras horizontales» pedido al copiloto cuesta hoy modelo + auditoría + sandbox para lo que
> es `orient="h"`.

```
# PROMPT PRO.8 (RED/GREEN) — El catalogo determinista cubre el grafico de un informe
# Deploy: edge (services/charts/, contracts/blocks.py, services/copilot/)

## Por que
Tres huecos, en este orden de importancia:

1. **Una plantilla no puede pedir un titulo.** El renderizador sabe poner titulo y etiquetas de
   eje —`ChartConfiguration` los tiene— pero `ChartBlockConfig`, que es lo que una plantilla
   expresa, solo pasa tipo, columnas, paleta, agregacion y formato. Un grafico de informe con
   `credito_inicial` como etiqueta del eje Y no es publicable, y ponerle titulo hoy exige
   generar codigo.
2. **`show_values` esta declarado y el renderizador no lo implementa.** En un informe
   presupuestario, las cifras encima de las barras son la norma. Un campo del contrato que no
   hace nada es peor que no tenerlo.
3. **Faltan tipos, y seis de los diez del legacy son parametros de lo que ya hacemos**: `barh`
   (ejes cambiados), `bar_grouped` (ya es `bar` con `color_by`), `line_multi` (ya es `line` con
   `color_by`), `bar_stacked` (pivot + una llamada), `donut` (un `wedgeprops`), `bubble`
   (`scatter` con `size=`). Dos son familia nueva y estandar: `boxplot` y `heatmap` —el heatmap
   es la forma mas institucional que hay: capitulo x anyo—.

## Que hacer
1. RED: un bloque CHART con titulo, etiquetas de eje, cifras encima y orden descendente sale
   con las cuatro cosas; y un `barh`, un `bar_stacked`, un `donut`, un `boxplot` y un `heatmap`
   se renderizan sin pasar por ningun modelo.
2. GREEN: `ChartBlockConfig` expone lo que el renderizador ya sabe hacer (titulo, etiquetas,
   leyenda, rejilla, tamanyo, bins, orden) y `ChartHandler._to_chart_config` lo mapea. Nada de
   campos nuevos en el servicio que la plantilla no pueda pedir: es el hueco que crea esto.
3. GREEN: `show_values` implementado.
4. GREEN: los ocho tipos. `violin` y `pairplot` **se quedan fuera**: son graficos de
   exploracion estadistica, y `pairplot` devuelve un grid que no encaja en `fig, ax`.
5. GREEN, y aqui esta el ahorro: `translate_nl_to_config("chart_config")` devuelve
   **configuracion declarativa** cuando la peticion cabe en el catalogo, y baja al script solo
   cuando no cabe. Mismo patron que PRO.4 aplico al ETL: JSON primero, script como ultimo
   recurso.

## Restricciones
- El script de grafico sigue pasando por el mismo auditor. Un camino con auditoria y otro sin
  ella es no tener auditoria.
- Sin pantalla de configuracion de graficos: quien elige el tipo es la plantilla o el modelo.
  Que una persona lo elija de una lista es otra decision y otra pantalla.

## Criterio de done
- [ ] Un informe con un grafico titulado, con etiquetas y cifras, y ordenado
- [ ] Los ocho tipos renderizan sin modelo
- [ ] Una peticion en lenguaje natural que cabe en el catalogo **no** genera script
```

---

### Prompt PRO.9 (RED/GREEN) — El ETL cubre lo que una hoja de cálculo necesita

**Modelo sugerido**: **Opus** — decide qué es expresable sin abrir una puerta a `eval`.

> **Añadido el 2026-08-17**, a petición del usuario: «el módulo ETL tiene sentido para
> transformar una hoja de cálculo en los datos que necesita el informe».
>
> Comprobado antes de planificar: **lo determinista del legacy está portado al 100%** en PRO.4
> —su catálogo de modelos son las once operaciones que ya están—. Lo que falta no es migración,
> es **cobertura**: ni el legacy ni nosotros cubrimos cuatro cosas que una hoja real necesita, y
> hoy cada una de ellas cuesta **tres intentos fallidos del modelo** (el prompt le dice que
> devuelva lista vacía si no cabe, y una lista vacía es un reintento) **más un script generado,
> auditado y ejecutado en el sandbox**.

```
# PROMPT PRO.9 (RED/GREEN) — Columna calculada, numeros de verdad, orden y unpivot
# Deploy: edge (services/transformation/)

## Por que
| Falta | Por que importa | Que pasa hoy |
|---|---|---|
| Columna calculada (`pct = obligaciones / credito * 100`) | Es **la** transformacion de un informe presupuestario | 3 reintentos + script |
| Numeros en formato espanyol (`"1.234,56 EUR"` llega como texto) | `groupby.sum()` sobre texto **concatena o revienta**: el informe sale con una cifra mal **y sin error** | 3 reintentos + script |
| Ordenar | Una tabla de informe se lee ordenada | 3 reintentos + script |
| Unpivot (cabeceras `ene feb mar` -> columna `mes`) | Las hojas institucionales son anchas y un informe necesita largo. Tenemos `pivot`, no el inverso | 3 reintentos + script |

La segunda es la peor porque **es silenciosa**: no hay error que mirar.

## Que hacer
1. RED: las cuatro operaciones, y en la de numeros un caso con `"1.234,56 EUR"` que despues
   suma bien.
2. GREEN: `compute_column` **sin evaluar expresiones**. Nada de `eval`, ni de `df.eval`, ni de
   un campo `formula`: el auditor de PRO.1 prohibe exactamente eso en un script, y un campo de
   formula seria una puerta trasera a lo mismo. Forma declarativa: columna o constante,
   operador de un conjunto cerrado, columna o constante, y un factor opcional. Lo compuesto se
   consigue **encadenando** —`t = a + b`, `pct = t / c`, `drop t`—, que es mas verboso y es
   auditable, y se puede pintar en una pantalla.
3. GREEN: `to_number` con separador decimal y de millares configurables (por defecto los de
   aqui: `,` y `.`) y simbolos a quitar. Lo que no se puede convertir queda vacio **y se ve**,
   como en `format_dates`; pero si **toda** la columna queda vacia eso es un error de
   configuracion, no un dato ausente: falla.
4. GREEN: `sort_values` (varias columnas, ascendente o descendente) y `unpivot`.
5. GREEN: el catalogo del prompt se genera solo (PRO.4 ya lo hace), asi que el modelo ve las
   nuevas sin tocar el prompt. Comprobarlo.

## Criterio de done
- [ ] Una hoja con importes como texto suma bien tras `to_number`
- [ ] `pct` calculada y visible en el informe, sin script generado
- [ ] Una instruccion en lenguaje natural con las cuatro **no** baja al script
- [ ] Cero `eval` en el camino
```

---
