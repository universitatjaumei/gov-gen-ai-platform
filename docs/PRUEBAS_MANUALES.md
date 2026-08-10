# Pruebas manuales de la plataforma completa

**Prompt MAN.1** (`Plan_TDD_Fase1.md`). Sustituye al modelo anterior de un `.bat` por bloque:
esos guiones caducaban en silencio cada vez que un bloque posterior renombraba una ruta o
rehacía una pantalla, y nadie había recorrido la plataforma de una pieza.

**Regla que no cambia** (CLAUDE.md §Verificación de UI): lo que el agente puede comprobar en
navegador **no entra** aquí. Esta matriz es sólo lo irreducible — credenciales e IdP reales,
sistemas externos no simulables, juicio subjetivo, lector de pantalla real y datos personales
de verdad.

---

## Hallazgos que requieren tu decisión (MAN.1 + MAN.2, para revisar juntos)

| # | Hallazgo | Estado | Alcance |
|---|---|---|---|
| 1 | `curation/SitesPage.tsx`: `useDeleteSite` no invalidaba la lista tras borrar (DELETE 204 en servidor, fila seguía en pantalla) | ✅ **Arreglado** (commit `6cba8fc`, test RED/GREEN) | 1 fichero |
| 2 | `GET /api/v1/hub/redaccion/templates` (y 5 sitios más del mismo router) devuelve **500** para cualquier sesión cuyo `user_id` no sea UUID — el SuperAdmin de desarrollo tiene `admin_id` entero y el Admin `partner_id` de texto libre, ninguno UUID | ✅ **Arreglado** — los 6 sitios de `hub_redaccion_router.py` usan ahora `_actor.user_to_uuid` (uuid5 determinista), el mismo patrón que ya aplicaban `llm_drafts_router.py` y `scripts_router.py` para este problema; se extrajo a un helper compartido para no triplicarlo. No era una decisión de diseño abierta: dar a SuperAdmin/Admin una identidad UUID real exigiría migrar `SuperAdminAccount.admin_id`/`AdminAccount.partner_id`, desproporcionado para este hallazgo. 5 tests nuevos en `tests/redaccion/test_hub_redaccion_router.py` | 3 ficheros de código + 1 test nuevo. De paso, arreglados dos rojos preexistentes destapados al tocar el módulo: `test_llm_drafts_router.py` no colectaba (`_PARTNER` con `role="partner"`, obsoleto desde el renombrado ROL.1→ROL.2) y una aserción esperaba `status == "draft"` donde el código, deliberadamente desde 9R.10.2, devuelve `"ingesting"` |
| 3 | El widget público (`frontend/src/widget/`) **no consume ningún tema** de organización/chatbot — `ThemeProvider` sólo está cableado en `frontend/src/App.tsx` (panel admin) | ✅ **Arreglado** — investigado primero: `HubChatbot.theme_config`/`HubOrganizacion.theme_config` eran columnas huérfanas (nadie las leía); el sistema real es `hub_themes_router.py` (temas en `data/themes/*.json`, cascada plataforma→organización→chatbot ya modelada), pero `apply_theme_to_chatbot` era un stub con `# TODO` que no persistía nada. Completado el stub (guarda `{"theme_id": ...}` en `theme_config`, reutilizada como puntero) y añadido `GET /hub/themes/for-chatbot/{chatbot_id}`: devuelve solo `config` (nunca `theme_id`/`organizacion_id`/`name`, para no reabrir el censo de organizaciones que SEC.5 cerró) y exige `assert_chatbot_access` (mismo criterio que `/hub/chat`). El widget (`main.tsx`) lo llama al montar y reutiliza `injectThemeCSS` de `ThemeProvider` (exportada para la ocasión), sin duplicar lógica de temas. Verificado en navegador de punta a punta: tema creado por API → aplicado a "Chatbot MAN Uno" → `--color-primary` inyectado en `:root` con el valor real (`#ff00aa`). 10 tests backend + 6 tests frontend nuevos, suite frontend completa **en serie: 281 passed, 0 failed** (`--no-file-parallelism`; en paralelo la suite da falsos rojos distintos en cada pasada — contención ya documentada en `PROJECT_STATE.md`, no relacionada con este cambio), `tsc --noEmit` limpio. **Pendiente para un prompt propio** (fuera de MAN.2, a petición del usuario): completar el editor de temas del panel admin con cabecera/logo — es la definición de la plantilla, no la resolución que consume el widget |
| 4 | "Ejecutar" en `/hub/test-scenarios` fija `fallback_reason=None` a propósito (línea 256 de `hub_test_scenarios_router.py`) — **no es un bug**, pero significa que las ejecuciones de escenarios de prueba **nunca** alimentan la detección de huecos de RAG.14. Sólo lo hace una conversación real (widget o `POST /hub/chat/{id}`) | ℹ️ Documentado, sin acción — es la separación correcta entre "revisión manual" y "señal de uso real" | Ninguno; queda anotado para que nadie repita la confusión |

---

## Ya verificado por el agente en navegador (2026-08-09) — no repetir

Con `docker compose up -d db`, backend en `:8000` y frontend en `:5173`, sesión real como
`fabra@uji.es`:

| Área | Qué se comprobó |
|---|---|
| Hub — Chatbots | Lista con datos reales (Chatbot Demo, Chatbot de Ejemplo) |
| Hub — Organizaciones | Lista con datos reales (2 organizaciones) |
| Hub — Documentos | Selector de chatbot, banner de retrieval, dropzone, tabla vacía |
| Hub — Informes | Estado vacío correcto (0 interacciones) |
| Hub — Modelos LLM | Proveedores (google/ollama/openrouter) y 4 configuraciones LLM |
| Hub — Prompts del sistema | Prompt base por chatbot + 3 plantillas es/ca/en de "Chatbot de Ejemplo" |
| Hub — Cerebro IA | Selector de modelo con el actual marcado (✓) |
| Hub — Escenarios de prueba | Selector de chatbot, estado vacío |
| Hub — Tokens de acceso | Estado vacío, formulario accesible |
| Curación — Sitios | Alta real de un sitio (POST 201), listado, disparo de rastreo (POST 202) |
| Curación — Auditoría | Informe se muestra al elegir sitio (GET 200), sin pasos intermedios |
| Curación — Hallazgos | Selector de sitio + panel de huecos de corpus (RAG.14) montado siempre |
| Curación — Publicación | Selector de sitio y chatbot, selecciones y candidatas vacías correctas |
| Automatización / Plataforma | Placeholders intencionados (Fase 1 no los cubre aún) |
| Widget | `widget.html` requiere `npm run build:widget`; tras construirlo, el input y "Enviar" renderizan |
| MCP | Suite propia `mcp_server/tests`: 54 passed |

**MAN.2 — recorrido de punta a punta (2026-08-09), datos reales creados en esta sesión:**

| Paso | Qué se hizo | Resultado |
|---|---|---|
| Organización nueva | `POST /hub/organizaciones` → "Organización MAN.2" | 201, aparece en la lista con 0 chatbots |
| Dos chatbots bajo la misma organización | "Chatbot MAN Uno" y "Chatbot MAN Dos" | 201 × 2, ambos Vectorial RAG / Activo |
| Ingesta de un PDF real | `ARQUITECTURA GEN-GOV.pdf` (240 KB) subido a "Chatbot MAN Uno" vía dropzone | Job pasa de "Procesando" a documento en el corpus, 4,8 k tokens, Docling + RapidOCR en los logs |
| Consulta real contra el LLM (Gemini, clave real configurada) | 3 preguntas sobre la arquitectura de despliegue vía Escenarios de prueba | El chatbot respondió (sin alucinar) "no tengo información suficiente… con citas verificables" las 3 veces — el PDF elegido es sobre todo diagramas, poco texto extraíble; ver hallazgo #4 sobre por qué esto NO alimentó la detección de huecos |
| `POST /hub/quality/gaps/analyze` contra el `GapFinding` corregido en CUR.1 | Ejecutado desde Curación → Hallazgos | 200 OK, 0 huecos (esperado, ver hallazgo #4) — confirma que el fix de CUR.1 no rompió el camino feliz con datos reales |
| Organización + 2 chatbots + 1 documento **se dejan sembrados** en la BD de desarrollo, por si quieres continuar la verificación de RAG.14 tú mismo repitiendo el paso de consulta desde el widget en vez de Escenarios de prueba | — | — |

**Nuevo `.bat` maestro**: `pruebas_manuales_plataforma.bat`, con menú (o parámetro `0`-`4`) para
los cuatro caminos cruzados de MAN.2. Probado en seco (`0`, `1`, `2`, `3`, `4`): arranca, hace
los `curl` reales y no se cuelga. Corregido en el proceso un bug propio del guion (faltaba el
salto para el parámetro `0`, y unos `^` de escape sobrantes en las cadenas de `curl` que hacían
salir un `^>` literal en vez de `->`).

---

## Matriz de lo irreducible

### `agents_hub` (RAG, ingesta de conversación, LangGraph)

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Respuesta real de un chatbot con corpus cargado y LLM en producción (Gemini/OpenRouter) | El coste y la clave de API son del usuario; el agente no debe gastar cuota ajena sin permiso | Alguien con las claves de API configuradas |
| Calidad subjetiva de una respuesta en valenciano/catalán frente a castellano | Juicio lingüístico — un test automático mide recall de citas, no naturalidad | Persona con criterio institucional en las tres lenguas |
| SSO SAML contra el IdP real de la UJI | Sin IdP de pruebas disponible; el flujo completo (redirect + assertion) no es simulable | Alguien con acceso al IdP institucional |

### `modules/automation` (flows, ETL, sandbox de scripts)

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Aislamiento de red real del `script-sandbox` Docker (sin DNS a `postgres`, sin salida a internet) | Exige inspeccionar `docker inspect` y ejecutar comandos dentro del contenedor prod; cubierto por `pruebas_manuales_promptSBX_4.bat`, vigente | Alguien con Docker Desktop y el stack `docker-compose.prod.yml` levantado |
| Ejecución de un script real contra un sistema externo (SharePoint, correo, ERP institucional) | Credenciales y sistemas reales de la UJI, no reproducibles en local | Alguien con acceso a esos sistemas |

### `modules/redaccion` (plantillas, borrador LLM, anonimización, exportación)

> ⚠️ **Bloqueado de raíz** (hallazgo #2 de la tabla de arriba): `GET /hub/redaccion/templates`
> devuelve 500 para cualquier sesión de desarrollo (SuperAdmin o Admin), así que ninguna fila
> de esta tabla se puede recorrer todavía sin arreglar antes ese endpoint.

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Calidad de la anonimización sobre un documento con datos personales reales | El agente no debe procesar PII real; los tests usan datos sintéticos | Alguien con un documento de prueba ya anonimizado por otra vía, o con autorización expresa para usar uno real |
| Fidelidad del borrador LLM generado frente a lo que un redactor humano esperaría | Juicio de calidad editorial, no verificable por regla | Persona con criterio de redacción institucional |
| Exportación final (DOCX/PDF) abierta en Word/Adobe reales, con la maquetación institucional | El agente puede comprobar que el fichero se descarga y su tamaño; no que "se vea bien" en el lector real | Cualquiera con Office/Adobe instalado |

### `frontend/widget` (chatbot público embebible)

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| El widget embebido en una página real de la UJI (no `widget.html` de laboratorio) | Requiere publicar el script en un dominio real de la universidad | Alguien con acceso a publicar en un sitio de la UJI |
| `pruebas_manuales_prompt9CBis11.bat` (citas como pills) contra un chatbot con corpus real | `widget.html` apunta a un `chatbot_id` de fixture (`E2E Bot`) que no existe en el seed de desarrollo actual — de ahí el 401 al preguntar. Hace falta un chatbot con API key pública y corpus cargado | Alguien que configure ese chatbot de prueba con datos reales |

### `themes` (identidad visual)

> ⚠️ **El widget no aplica ningún tema todavía** (hallazgo #3 de la tabla de arriba): esto no es
> "irreducible" en el sentido de MAN.1 — no es que el agente no pueda juzgarlo, es que el código
> que lo haría posible no existe aún fuera del panel admin. Las dos filas de abajo son las que
> serán irreducibles **una vez** exista esa pieza.

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Tipografía, color y tono del texto frente a la identidad visual institucional de la UJI | Juicio subjetivo de diseño; el agente puede comprobar que el tema carga, no si "es la UJI" | Diseño / comunicación institucional |
| El tema de una organización aplicado al widget en una página real | Depende del punto anterior (widget en dominio real) | Igual que el punto anterior |

### Servidor MCP (`mcp_server/`)

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Conexión real desde un cliente MCP (Claude Desktop, Cursor…) por stdio | No tiene superficie HTTP ni de navegador; es un proceso stdio que un cliente MCP lanza | Alguien con un cliente MCP instalado y `docs/MCP_SERVER.md` a mano |
| Autoría de una plantilla de redacción de principio a fin usando las tools MCP desde un cliente real | Igual que el punto anterior — el agente puede (y ha) probado las 54 tests automáticas, no la experiencia de uso real | Igual que el punto anterior |

### `client_app` (agente de ejecución local)

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| El agente local ejecutándose de verdad en la máquina de un usuario final, con su propio watcher de carpeta | Es un proceso de escritorio separado, fuera del navegador; requiere arrancarlo e interactuar con el sistema de ficheros real | Alguien con `client_app` instalado en su máquina |
| Comunicación WebSocket edge↔cloud con el grafo orquestando y el edge ejecutando (invariante de arquitectura) | Requiere dos procesos reales (cloud + edge) hablando entre sí; no es una pantalla | Alguien con ambos entornos desplegados |

### Despliegue `DEPLOY_MODE=cloud|edge`

| Qué se prueba | Por qué NO lo hace el agente en navegador | Quién |
|---|---|---|
| Que arrancando con `DEPLOY_MODE=edge` los routers cloud (auth admin, organizaciones, temas) de verdad no responden | Exige levantar el servidor dos veces con variables de entorno distintas; no es una prueba de un único navegador con sesión ya iniciada | Alguien con dos arranques del backend, o esperar a D.0-D.5 y probarlo contra el despliegue real (MAN.4) |

---

## Lo que YA no necesita entrar aquí (cubierto por otra vía)

- Cualquier pantalla del Hub o de Curación con datos ya sembrados: cubierto en la tabla de
  arriba y en los tests de componente (Vitest) de cada pantalla.
- Accesibilidad automática (contraste, roles ARIA, `<label>` asociado): la cubre el gate de
  `axe` en CI desde la Fase 20. Lo que **no** cubre axe —orden del foco, que el lector de
  pantalla anuncie el nombre correcto— va en MAN.3, no aquí.
- Paridad de traducción es/ca/en: la cubren los guardarraíles `adminI18nCoverage.test.ts` y
  `curationI18nCoverage.test.ts`.
- Seguridad de cabeceras, límite de peticiones, aislamiento multi-tenant: cubierto por los
  tests automáticos del Bloque SEC; lo irreducible de SEC ya vive en
  `pruebas_manuales_bloqueSEC.bat` (vigente, con la única corrección de ruta de esta sesión).

---

## `.bat` de la raíz: inventario (MAN.1)

| Fichero | Estado | Motivo |
|---|---|---|
| `pruebas_manuales_bloqueFASE11.bat` | Vigente | Instalación one-click; `bootstrap.py` sigue creando "Chatbot de Ejemplo" con 3 prompts tal como describe |
| `pruebas_manuales_bloqueRAG.bat` | Vigente (corregido) | La sección de huecos de corpus apuntaba a `/hub/content-quality`, retirado por CUR.2; corregido a `/curation/findings` |
| `pruebas_manuales_bloqueSEC.bat` | Vigente (corregido) | El paso 5 apuntaba a `/admin/chatbots`, una ruta que nunca existió (siempre fue `/hub/chatbots`); corregido. Migración `s6b7c8d9e0f1` sigue siendo head |
| `pruebas_manuales_prompt9CBis11.bat` | Vigente | El widget y sus pills de citas no los ha tocado ningún bloque desde 9CBis.11 |
| `pruebas_manuales_prompt9CBis8.bat` | **Borrado** | Describía subir un PDF desde una pestaña "Documentos" dentro de la edición del chatbot; esa UI la sustituyó por completo la página `/hub/documents` independiente (CAL.1-CAL.4) |
| `pruebas_manuales_prompt9CBis9.bat` | **Borrado** | Describe la tab "Fuentes web" dentro de Documentos, retirada por CAL.2, y el layout de la tabla que CAL.3/CAL.4 rehicieron |
| `pruebas_manuales_prompt9Q_9.bat` | **Borrado** | Rutas `/hub/sites` y `/hub/content-quality` movidas por CUR.2 a `/curation/*`; el "panel de mapeo" anidado bajo una fila de sitio ya no existe, ahora es la página `Publicación` independiente. Su contenido queda cubierto por la tabla de "ya verificado" de arriba |
| `pruebas_manuales_promptAUTH_4.bat` | Vigente | Login, tokens de acceso y SSO opcional sin cambios desde AUTH.4 |
| `pruebas_manuales_promptFIX1.bat` | Vigente | Selector de modelo y escenarios de prueba sin cambios desde FIX.1 |
| `pruebas_manuales_promptROL_2.bat` | Vigente | Renombrado Partner→Admin, Client→Organización sin cambios desde ROL.2 |
| `pruebas_manuales_promptSBX_4.bat` | Vigente | Aislamiento Docker del sandbox, infraestructura no tocada por ningún bloque posterior |
| `pruebas_manuales_plataforma.bat` | **Nuevo (MAN.2)** | `.bat` maestro con menú/parámetro para los 4 caminos que cruzan módulos; ver la sección MAN.2 más arriba |
