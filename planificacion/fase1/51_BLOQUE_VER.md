## Bloque VER — Verificación de Informes y Curación antes del despliegue

> **Planificado el 2026-08-17**, a petición del usuario: «no hemos hecho pruebas manuales
> mediante Chrome in Claude primero y con intervención humana después del módulo de informes
> y del de curación. ¿Valdría la pena probarlos en local antes del deployment?».
>
> Sí, y por una razón que la propia planificación demuestra: al ir a prepararla apareció que
> **Informes no genera nada**. Eso no se descubre leyendo tests verdes, se descubre
> recorriendo la aplicación, y descubrirlo después del despliegue cuesta mucho más.

Los dos módulos llegan al despliegue **sin haber sido recorridos nunca de una pieza**. Los
Caminos 3 y 4 (2026-08-14) los rozaron y sacaron cinco fallos —cinco de cinco intentos—, lo
que dice bastante sobre lo que queda por encontrar. Este bloque los recorre enteros: primero
el agente en navegador, arreglando lo que aparezca con TDD; el humano solo al final, y solo
para lo irreducible.

### Lo medido el 2026-08-17, antes de planificar

No hay que volver a averiguarlo:

| Qué | Estado real |
|---|---|
| Superficie de los dos módulos | **62 de los 126 endpoints** del contrato |
| `POST /redaccion/workspaces/{id}/run` | **No ejecuta el grafo.** Transiciona a `drafting` y devuelve un `run_id` sintético (`workspace_run_service.py:183`: «Para el MVP no dispara la ejecución del grafo en background») |
| `DraftingCoreGraph` | **Construido y completo** (14 nodos: extracción determinista, transformación, calidad de datos, anonimización, redacción con IA, citas, revisión, ensamblado). Solo le faltan las dependencias inyectadas |
| `POST /redaccion/llm-drafts/propose` | **503** — `get_llm_spec_service` es un stub sin cablear |
| `POST /redaccion/scripts/propose` | **503** — `get_script_proposal_service` es un stub sin cablear |
| `POST /redaccion/copilot/ask` | **503** — `get_copilot_service` es un stub sin cablear |
| Curación | **Cableada entera**: `main.py` registra crawler, detectores y planificador en el arranque |

### Decisión del usuario (2026-08-17)

**Se cablea la generación y luego se prueba.** Entra: ejecución real del grafo y
`llm-drafts/propose`. **Queda fuera, documentado**: el copiloto de redacción y la propuesta
de scripts por LLM — son tres motores distintos y ninguno de los dos últimos hace falta para
producir un informe.

### Prerrequisitos

- Docker con la base de desarrollo y el contenedor `script-sandbox` en marcha.
- Backend en `:8000` y frontend en `:5173`, **reiniciados**: la sesión del 2026-08-16 dejó un
  backend sirviendo código anterior.
- **Objetivo del crawl: el sitio local del corpus en `http://127.0.0.1:4174/`**, no
  `www.uji.es`. Es HTML institucional real, responde sin límite de peticiones y no cambia
  entre dos ejecuciones, así que un fallo es del código y no del sitio. La página real queda
  como paso humano al cierre.
- Credenciales de Vertex (ADC) ya presentes, las mismas del Bloque PIL.

---

### Prompt VER.1 (RED/GREEN) — La generación de informes se ejecuta de verdad

**Modelo sugerido**: **Opus** — hay que componer un grafo de 14 nodos con siete dependencias y
decidir dónde vive esa composición; equivocarse ata el módulo al router.

```
# PROMPT VER.1 (RED/GREEN) — Raiz de composicion del DraftingCoreGraph y ejecucion real
# Deploy: edge (modules/redaccion)

## Por que
`POST /redaccion/workspaces/{id}/run` promete una ejecucion y no la hace: cambia el estado a
`drafting`, devuelve un `run_id` que no identifica nada y ahi acaba. Para quien usa el panel
esto es indistinguible de un informe que tarda, y esperara indefinidamente.

El grafo NO hay que escribirlo: `build_core_graph()` existe, con sus 14 nodos y sus tests. Lo
que falta es la **raiz de composicion** —quien le pasa el repositorio de versiones, el
almacenamiento, la factoria de extraccion, el LLM y el repositorio de manifiestos— y el
disparo en segundo plano.

## Que hacer
1. RED: test que llama a `POST /run` sobre un workspace con inputs subidos y exige que, al
   terminar la ejecucion, los bloques del workspace tengan contenido y exista un
   `RunManifest` persistido con ese `run_id`. Hoy falla: no se escribe nada.
2. GREEN: `build_drafting_graph(deps)` en el punto de integracion del modulo —el equivalente
   de `build_agentic_loop_if_needed` en el chatbot—, resolviendo `llm_service` por
   `model_factory` y `extraction_factory` por la factoria de pipelines que ya existe.
   Ejecucion con `BackgroundTasks`, como hace `hub_ingestion_router` en la subida.
3. El estado terminal se persiste: `drafting -> review` al terminar, y **un estado de error
   explicito si el grafo lanza**. Un workspace atascado en `drafting` para siempre es peor
   que uno que dice que fallo.
4. `GET /workspaces/{id}` refleja lo generado sin que el frontend tenga que adivinar nada.

## Restricciones
- Nada de rutas nuevas: el contrato de `RunStartedOut` no cambia.
- El LLM se resuelve por `Depends`, no se instancia dentro de la logica.
- Si el modelo no esta configurado, el error viaja al workspace, no revienta la peticion.

## Criterio de done
- [ ] `POST /run` produce bloques y manifiesto reales sobre la base de desarrollo
- [ ] Un fallo del grafo deja el workspace en estado de error, con el motivo
- [ ] Suite de `tests/redaccion` verde
```

---

### Prompt VER.2 (RED/GREEN) — Proponer una plantilla con el LLM

**Modelo sugerido**: **Sonnet** — el alcance está cerrado: un stub, un servicio ya escrito y
tres endpoints que ya existen.

```
# PROMPT VER.2 (RED/GREEN) — llm-drafts enchufado a model_factory
# Deploy: edge (routers/redaccion/llm_drafts_router.py)

## Por que
`LLMSpecService` esta escrito y probado; lo que devuelve 503 es la dependencia que lo
construye. Es la puerta de entrada natural al modulo: describir el informe que quieres y que
la plantilla se proponga sola, en vez de montarla campo a campo en el constructor.

## Que hacer
1. RED: test de API que llama a `/llm-drafts/propose` con un doble del modelo y espera 200 con
   una plantilla valida contra el esquema.
2. GREEN: `get_llm_spec_service` resuelve el modelo por `model_factory`, igual que el resto del
   proyecto.
3. Recorrer los tres pasos del camino: `propose` -> `validate` -> `approve-as-template`, y que
   la plantilla aprobada aparezca en `/redaccion/builder`.

## Criterio de done
- [ ] Los tres endpoints responden sin 503 con el modelo configurado
- [ ] Sin modelo configurado, el 503 sigue siendo explicito y dice que falta
```

---

### Prompt VER.3 (verificación en navegador) — Informes A: plantilla y contrato SDUI

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.3 — Camino de Informes A, en navegador

## Que recorrer
`/redaccion/builder`: crear una plantilla, anadirle version, y comprobar que
`GET /template-versions/{id}/ui-contract` devuelve el contrato y que el asistente
(`/redaccion/wizard`) **construye el formulario iterando sobre el**, sin campos fijos.

Es la regla maestra n.1 del proyecto (SDUI). Si aqui aparece un campo hardcodeado en React, es
un fallo de arquitectura, no de estilo.

## Como
Extension de Chrome: `navigate`, `read_page`/`find` para el contenido, `computer`/`form_input`
para interactuar, y `read_console_messages` + `read_network_requests` en cada pantalla. Un 500
en la consola cuenta como hallazgo aunque la pantalla se vea bien.

## Que hacer con lo que aparezca
Arreglarlo aqui mismo con TDD —repro, rojo, arreglo, suite, verificacion en vivo—, no apuntarlo
para despues. Es lo que se hizo con los cinco hallazgos del 2026-08-14.

## Criterio de done
- [ ] Plantilla creada y versionada desde la interfaz, con evidencia
- [ ] Formulario del asistente generado desde el contrato, no desde codigo
- [ ] Consola y red limpias en las dos pantallas
```

---

### Prompt VER.4 (verificación en navegador) — Informes B: del documento subido al informe exportado

**Modelo sugerido**: **Opus** — es el camino largo y el que cruza más piezas.

```
# PROMPT VER.4 — Camino de Informes B, en navegador

## Que recorrer, de punta a punta
1. Crear workspace desde una plantilla y ver los **slots de subida** que el contrato declara.
2. Subir un documento de prueba (sintetico, nunca con datos personales reales).
3. Lanzar la generacion (VER.1) y ver el estado avanzar sin quedarse colgado.
4. **Panel de calidad de datos** y preguntas por datos que faltan.
5. **Panel de anonimizacion**: resumen, cambio de modo y re-analisis.
6. **Revision de bloques**: aprobar, rechazar, regenerar y editar; el anunciador de estado y el
   modal de conflicto.
7. **Preview** e impresion (`/redaccion/workspaces/{id}/preview`).
8. **Exportacion** y comprobacion de que el fichero se descarga y no esta vacio.

## Restriccion de datos
Documento de prueba sintetico. La calidad de la anonimizacion sobre datos personales reales es
paso humano y ya esta en `docs/PRUEBAS_MANUALES.md`.

## Criterio de done
- [ ] Los ocho pasos recorridos con evidencia
- [ ] Ningun estado terminal indefinido
- [ ] Hallazgos arreglados con TDD, no listados
```

---

### Prompt VER.5 (verificación en navegador) — Informes C: la cola de aprobación de scripts

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.5 — Camino de Informes C, en navegador

## Contexto
`POST /scripts/propose` sigue en 503 a proposito (queda fuera del alcance de este bloque), asi
que la propuesta se **siembra en base de datos**, como se hizo en el Camino 4. Lo que se
verifica es el ciclo que si existe: datos de prueba -> anonimizado -> sandbox -> validacion ->
envio a revision -> re-test del administrador -> aprobacion o rechazo.

## Ojo con esto
El re-test compara hashes de reproducibilidad y ya bloqueo la aprobacion de cualquier script
una vez (decimo hallazgo del 2026-08-14). Comprobar que **aprobar sigue siendo posible**, no
solo que la pantalla pinta.

## Criterio de done
- [ ] Un script recorre el ciclo hasta aprobado, con el sandbox real
- [ ] El rechazo tambien funciona y deja el motivo
- [ ] La plantilla destino se puede elegir (arreglado el 2026-08-15; comprobar que sigue)
```

---

### Prompt VER.6 (verificación en navegador) — Curación A: sitio, crawl y candidatos

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.6 — Camino de Curacion A, en navegador

## Que recorrer
`/curation/sites`: alta de sitio apuntando a `http://127.0.0.1:4174/` —el sitio del corpus
publicado—, lanzar el crawl, y comprobar en `/pages` y `/candidates` que las paginas aparecen.
Editar y borrar el sitio (el borrado ya fallo una vez por no invalidar la lista: comprobar que
la fila desaparece de verdad).

## Por que este objetivo y no uji.es
Es HTML institucional real, responde sin limite de peticiones y no cambia entre dos ejecuciones,
asi que un fallo es del codigo y no del sitio. La pagina real queda como paso humano al cierre.

## Criterio de done
- [ ] Sitio creado, rastreado y con paginas listadas, con evidencia
- [ ] Borrado reflejado en pantalla sin recargar
```

---

### Prompt VER.7 (verificación en navegador) — Curación B: análisis, hallazgos e informe

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.7 — Camino de Curacion B, en navegador

## Que recorrer
`/curation/audit`: lanzar el analisis del sitio y ver el informe de calidad.
`/curation/findings`: la cola de revision y **las tres transiciones** (confirmar, descartar,
resolver), incluida la que debe devolver 422 por invalida.
Exportacion del informe en DOCX y en PDF, comprobando que el fichero baja y no esta vacio —y
que el PDF cae a DOCX de forma visible si no hay LibreOffice, en vez de dar un fichero roto—.

## Criterio de done
- [ ] Analisis ejecutado y hallazgos listados
- [ ] Las tres transiciones validas y el rechazo de la invalida
- [ ] Los dos formatos de exportacion descargados
```

---

### Prompt VER.8 (verificación en navegador) — Curación C: huecos, caducidades y publicación

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.8 — Camino de Curacion C, en navegador

## Que recorrer
1. **Huecos de corpus** (`/hub/quality/gaps`): lanzar el analisis sobre un chatbot con
   conversaciones reales —las hay del piloto— y ver los grupos de preguntas sin respuesta.
2. **Caducidades** (`/hub/quality/stale`): lanzar el analisis y contrastar el resultado con la
   pantalla de Vigencia (A7), que mide algo distinto sobre el mismo corpus. Si los dos numeros
   se contradicen, eso es el hallazgo.
3. **Publicacion** (`/curation/publish`): seleccionar paginas candidatas y publicarlas en un
   chatbot; comprobar que llegan al corpus de ese chatbot y **solo de ese**.

## Criterio de done
- [ ] Los tres caminos recorridos con evidencia
- [ ] La relacion entre caducidad y vigencia, escrita
```

---

### Prompt VER.9 (cierre) — Lo irreducible, el `.bat` y el informe

**Modelo sugerido**: **Sonnet**.

```
# PROMPT VER.9 — Cierre del bloque VER

## Que hacer
1. Actualizar `docs/PRUEBAS_MANUALES.md`: mover a «ya verificado por el agente» todo lo
   recorrido, y dejar en la matriz solo lo irreducible —calidad editorial del borrador,
   anonimizacion sobre datos personales reales, exportacion abierta en Word y Adobe reales, y
   un crawl contra `www.uji.es` de verdad—.
2. Generar `pruebas_manuales_bloqueVER.bat` en la raiz, **ANSI sin BOM** (escrito con
   PowerShell y `Encoding 1252`; verificar que empieza por `@ech` y no por un BOM).
3. Informe de cierre: prompts cerrados y commits, cifras reales de tests, que se verifico en
   navegador con que evidencia, desviaciones documentadas y las instrucciones de pruebas
   manuales.

## Criterio de done
- [ ] `PRUEBAS_MANUALES.md` sin nada que el agente ya haya comprobado
- [ ] `.bat` con la codificacion verificada
- [ ] Informe de cierre entregado
```

---
