| **Bloque NIC** — Retirada del legacy NiceGUI, con inventario antes de borrar | — | NIC.1 (**después de Deploy**) |# Estado del Proyecto — Gov Gen AI Platform

> Actualizado automáticamente al final de cada prompt de desarrollo.
> Fuente de verdad para saber en qué paso está cada plan activo.

---

## Planes activos

### Plan_Contrato_OpenAPI.md — Alineación Backend/Frontend con OpenAPI + Orval

| Bloque | Último completado | Siguiente | Estado |
|--------|-------------------|-----------|--------|
| CF.1 — Exportación OpenAPI | CF.1.2 ✅ | — | ✅ Completo |
| CF.2 — Orval + generación | CF.2.3 ✅ | — | ✅ Completo |
| CF.3 — Compilación TypeScript | CF.3.3 ✅ | — | ✅ Completo |
| CF.4 — Formulario piloto Chatbot | CF.4.4 ✅ | — | ✅ Completo |
| CF.5 — CI | CF.5.2 ✅ | — | ✅ Completo |

**Plan completo (CF.1–CF.5). No tiene cursor propio.** El único cursor vivo del proyecto es el de `Plan_TDD_Fase1.md`, en la sección siguiente. *(Esta línea decía «Cursor actual: 9B.6» desde que se cerró este plan; 9B quedó completo en 9B.14 y el puntero llevaba meses obsoleto, engañando a quien leyera el fichero de arriba abajo. Limpiado el 2026-07-30.)*

---

### Plan_TDD_Fase1.md — Hub Informativo, Personalización y Redacción (MVP)

| Bloque | Último completado | Siguiente | Modelo sugerido siguiente | Estado |
|--------|-------------------|-----------|---------------------------|--------|
| Fase 0 — Infraestructura | — | — | — | ✅ Eliminada (heredada) |
| Subfase 1.A — Chatbots Públicos (9B) | 9B.14 ✅ | — | — | ✅ Completo |
| Redacción Contract-First (9R) | 9R.10.2 ✅ | — | — | ✅ Completo (vertical slice MVP GREEN) |
| Subfase 1.B — Identidad Visual | 10.11 ✅ | — | — | ✅ Completo — Fase 10 (temas/plantillas) |
| Subfase 1.C — Privacidad, Diseño y Exportación | 1C.4 ✅ | — | — | ✅ Completo — 1C.0–1C.4 |
| Fase 13 — NER reversible en redacción | 13.2 ✅ | — | — | ✅ Completo |
| Fase 20 reducida — WCAG transversal | 20.2 ✅ | — | — | ✅ Completo — 9/9 tests verdes, CI gate activo, A11Y_CHECKLIST.md creado |
| Bloque SBX — Sandbox aislado de scripts | SBX.4 ✅ | — | — | ✅ Completo — SBX.1+SBX.2+SBX.3+SBX.4 cerrados |
| Bloque 9Q — **Motor de auditoría de sitios web** (antes «Calidad de Contenido Web Ingestado») | 9Q.9 ✅ | — | — | ✅ Completo — 9Q.0–9Q.9 cerrados. **Alcance reescrito el 2026-08-02** (`docs/DECISION_CURACION_SEPARADA.md`): el código no cambia, cambia de qué es parte. Deja de ser «calidad del contenido ingerido al servicio del RAG» y pasa a ser **el motor de la herramienta de curación**, que es previa al asistente. La salida principal es el **informe de auditoría** —vale por sí solo, sin chatbot—; la higiene del retriever es el efecto secundario. **No hay ingesta automática de web a corpus**: una página nueva es señal para el curador, no disparador. Ya estaba latente en su propio modelo —`HubWebSite` cuelga de `organizacion_id` y no tiene `chatbot_id`—. El movimiento de código va en el Bloque CUR |
| Bloque AUTH — SSO SAML + PAT (adelanto 1.B.1) | AUTH.4 ✅ | — | — | ✅ Completo — AUTH.1-AUTH.4 (SP SAML + provisioning + PAT/auth dual + UI login SSO/gestión PAT). Backend 43 tests + frontend 8 tests verdes |
| Bloque MCP — Servidor MCP stdio (plantillas+chatbots+test_chat) | MCP.4 ✅ | — | — | ✅ Completo — MCP.1-MCP.4 (scaffolding + tools plantillas/chatbots/test_chat + docs/MCP_SERVER.md). 16 tools + 5 resources, 54 tests MCP verdes |
| Bloque ROL — Renombrado institucional (Partner→Admin, Client→Organización) | ROL.2 ✅ | — | — | ✅ Completo — ROL.1 (backend) + ROL.2 (frontend: Orval regen, rutas /organizaciones, i18n es/ca/en, roles superadmin/admin). tsc sin errores, Vitest verde |
| Fase 11 — Autoinstalación y Distribución | 11.3 ✅ | — | — | ✅ Completo — 11.1 (generate_env.sh + .env.example), 11.2 (docker-compose.prod.yml one-click) y 11.3 (setup.sh + bootstrap idempotente). Suite `tests/infra`: 58 passed, 0 skipped |
| Bloque SEC — Endurecimiento de seguridad (bloqueante de despliegue) | SEC.7 ✅ | — | — | ✅ **Completo (2026-08-03)** — los 9 prompts: SEC.1 (contraseña en el login de Admin), SEC.2 (aislamiento entre organizaciones), SEC.2.1 (modo de acceso por chatbot + identidad delegada), SEC.3 (CORS por entorno), SEC.4 (límite de peticiones, contabilidad de tokens y cuotas), SEC.4.1 (vigencia y presupuesto), SEC.5 (temas), SEC.6 (validación de subidas, adelantado) y SEC.7 (docs off + cabeceras). **Pendientes las pruebas manuales del bloque.** ~~SEC.1~~, ~~SEC.2~~, ~~SEC.2.1~~, ~~SEC.3~~, ~~SEC.4~~, ~~SEC.4.1~~, ~~SEC.5~~, ~~SEC.7~~, SEC.4, **SEC.4.1**, SEC.5, SEC.6, SEC.7 (login con password A1, aislamiento multi-tenant A2, **modo de acceso por chatbot + identidad delegada**, CORS, **contabilidad de tokens + cuotas multi-sujeto**, **vigencia y presupuesto por chatbot**, temas, uploads, docs/headers). Planificado 2026-07-11, ampliado 2026-07-27 |
| **FIX.1** — El modelo de un chatbot no se puede cambiar | FIX.1 ✅ | — | — | ✅ **Completo (2026-08-02)** — detalle en el historial. ~~Pendiente— **añadido el 2026-08-02** desde las pruebas manuales del Bloque RAG, que quedaron bloqueadas. Un síntoma («el botón de ejecutar no hace nada») tapaba cuatro fallos: `gemini-2.0-flash` retirado por Google (404), el 500 de la ejecución invisible porque la mutación no tiene `onError`, `llm_config_id` **hardcodeado en el formulario y ausente de `ChatbotUpdate`** —la API no permite cambiar el modelo—, y el 409 al marcar por defecto en vez de demotar la anterior. **Riesgo latente**: editar cualquier chatbot en la UI le reasigna el modelo en silencio |
| Bloque CUR — La curación como producto propio | CUR.2 ✅ | — | — | ✅ **Completo (2026-08-09)** — decisión en `docs/DECISION_CURACION_SEPARADA.md`. CUR.1 mueve `ingestion/quality/` + spiders a `modules/curation/` (el `gap_detector` **se queda** en `agents_hub/ingestion/`: es la señal que el asistente emite hacia la curación); CUR.2 le da superficie y navegación propias en el frontend (`frontend/src/curation/`: Sitios, Auditoría, Hallazgos, Publicación) y hace explícito el paso de publicación (`CorpusSelectionService` → `PublicationPage`, cada candidata con su propio botón). **No reescribe nada y no toca el esquema.** **Suite backend completa con Docker levantado: 1697 passed, 1 skipped, 0 failed** — el primer pase sin BD (1414 passed, 280 skipped) escondía una regresión real en `GapFinding` (faltaban `site_id`/`page_id`, que un test de 9Q sigue comprobando), corregida en `d9ed15f` al re-ejecutar contra Postgres real. Suite frontend completa en serie: **274 passed, 0 failed**, `tsc --noEmit` limpio |
| Bloque CAL — Deuda de calidad pre-repo público | CAL.4.1 ✅ | — | — | ✅ **Completo (2026-08-09)** — CAL.1 (retirar NiceGUI del árbol activo + Caso B en client_app), CAL.2 (capa API del frontend desde el contrato, **cierra CF.4**), CAL.3 (descomponer `DocumentsPage`), CAL.4 (i18n `ca` a paridad + etiquetas accesibles), CAL.5 (carga por ruta + retirada de shims, más el borrado de los 3 scripts huérfanos) y **CAL.4.1** (las 41 claves de la pantalla de documentos que vivían sólo como *default*, subidas a `es/ca/en admin.json`; nuevo guardarraíl `should_not_keep_admin_keys_only_as_inline_default` que el test de paridad no podía cazar por construcción). **Suite frontend completa en serie: 264 passed, 0 failed. tsc --noEmit sin errores.** Planificado 2026-07-11 |
| Bloque MAN — Validación manual de la plataforma completa | MAN.1 ✅ | MAN.2 (falta ejecución humana) | Sonnet | ▶ **MAN.1 completo (2026-08-09)**: inventario de los 11 `.bat` de la raíz — 3 borrados por caducados, 2 corregidos por ruta muerta, 6 vigentes. `docs/PRUEBAS_MANUALES.md` con la matriz por módulo. Recorrido real en navegador (Hub + Curación completos, MCP 54 tests, widget construido) **destapó y corrigió un bug real** (`6cba8fc`, `SitesPage`/`useDeleteSite` sin invalidar la lista). **MAN.2 con el `.bat` maestro escrito y probado en seco** (`pruebas_manuales_plataforma.bat`, commit `aaf3b86`) y **recorrido en vivo de los caminos 1 y 2** con datos reales (organización, 2 chatbots, PDF ingerido, consultas reales a Gemini, `GapFinding` de CUR.1 ejercitado con 0 huecos esperados). **Hallazgo #2 arreglado (2026-08-10)**: el 500 de `GET /hub/redaccion/templates` (y 5 sitios más) para SuperAdmin/Admin con `user_id` no-UUID — los 6 sitios de `hub_redaccion_router.py` usan ahora el `_actor.user_to_uuid` compartido (uuid5 determinista) que `llm_drafts_router.py`/`scripts_router.py` ya aplicaban; no era una decisión de diseño abierta, era el mismo patrón sin aplicar de forma consistente. De paso, arreglados dos rojos preexistentes que este mismo módulo tenía escondidos (`test_llm_drafts_router.py` no colectaba por un fixture con rol obsoleto de antes de ROL.1/ROL.2; una aserción esperaba `"draft"` donde el código deliberadamente da `"ingesting"` desde 9R.10.2). 5 tests nuevos, `tests/redaccion` completo: 129 passed. Detalle en `docs/PRUEBAS_MANUALES.md` §Hallazgos. **Hallazgo #3 arreglado (2026-08-10)**: el widget público no consumía ningún tema. La investigación destapó que `HubChatbot`/`HubOrganizacion.theme_config` eran columnas huérfanas y que el sistema real de temas (`hub_themes_router.py`, cascada plataforma→organización→chatbot ya modelada) tenía `apply_theme_to_chatbot` como stub sin persistir (`# TODO`) — completado (guarda `{"theme_id":...}` en `theme_config`) más `GET /hub/themes/for-chatbot/{chatbot_id}` nuevo, que solo devuelve `config` (SEC.5 había cerrado la lectura pública de temas por censo de organizaciones; este endpoint no la reabre) y exige `assert_chatbot_access` como `/hub/chat`. El widget reutiliza `injectThemeCSS` de `ThemeProvider` (exportada para la ocasión) al montar. Verificado en navegador de punta a punta con un tema real aplicado. 10 tests backend + 6 frontend nuevos. **Descubierta de paso una contención preexistente de vitest en paralelo** (falsos rojos distintos en cada pasada, ya la documentaba la nota de abajo de este mismo fichero para A11y.test.tsx): confirmado que en serie (`--no-file-parallelism`) da 281/281, igual que las cifras "en serie" de cierres anteriores (CUR.2, CAL.4.1) — no es una regresión de este cambio. **Alcance explícitamente aparcado a petición del usuario**: completar el editor de temas del panel admin con cabecera/logo va en un prompt propio — es la definición de la plantilla, no la resolución que consume el widget. **Falta el criterio de cierre de MAN.2**: que el usuario ejecute el `.bat` de principio a fin. Pendientes: MAN.3 (lector de pantalla real + identidad visual) y MAN.4 post-deploy |
| Bloque SEC.8 — Endurecimiento pre-deploy (2ª auditoría) | SEC.8.5 ✅ | — | — | ✅ **Completo (2026-08-10)** — los 8 prompts. SEC.8.0 gate del sembrado de desarrollo (`56d5ef4`), SEC.8.1 IDOR horizontal en los routers post-SEC.2 (`1784519` + `391b23a`), SEC.8.2 subidas (`77c2a24`), SEC.8.3 sandbox y auditor AST (`97baafc`), SEC.8.4 proxy/secreto/SAML (`754127f`), SEC.8.6 temas en BD (`c604086`), SEC.8.7 tests de la raíz (`bd36e81`), SEC.8.8 crawler cableado (`4239ad9`) y SEC.8.5 credencial de sitio del widget (`8d10e79`). **Suite backend completa: 1782 passed, 1 skipped, 0 failed. Frontend en serie: 276 passed, 0 failed. `tsc --noEmit` limpio.** Dos migraciones aplicadas (`t7c8d9e0f1g2` temas, `u8d9e0f1g2h3` credenciales de widget). **Lección de método**: cerrar SEC.8.1 verificando solo `tests/api` dejó 30 rojos que la suite completa destapó — los directorios que toca un prompt incluyen los tests unitarios de los routers, no solo los de su superficie | ▶ **BLOQUEANTE DE DESPLIEGUE, va antes de D.0**. Nace de `docs/AUDITORIA_PRE_DEPLOY.md` (2026-08-10). **SEC.8.0 hecho** (`56d5ef4`): gate del sembrado de desarrollo (CR-1, el superadmin `fabra@uji.es`/`admin1234` ya no se siembra fuera de `development`). Pendientes SEC.8.1–SEC.8.8: aislamiento multi-tenant en los routers post-SEC.2 (CR-2 + IDOR horizontal, **Opus**), subidas (path traversal + validate_upload), sandbox (gate prod + auditor AST), cabeceras/SAML/JWT placeholder, widget sin Bearer privilegiado, temas persistentes en BD (B1), limpieza de los 14 tests rotos de la raíz `tests/` (B3), y decisión sobre el crawler de curación (B2). Prompts en `Plan_TDD_Fase1.md` §Bloque SEC.8 |
| **Bloque EXT** — Frontera de la extracción (corpus vs contexto) | EXT.3 ✅ | — | — | ✅ **Completo (2026-08-11)** — EXT.1 (`b9c2a94`) al corpus solo `.md` del contrato, EXT.2 (`66acd4a`) contexto con pdfplumber y guarda de escaneado, EXT.3 retirada de Docling y medición. **Suite backend: 1796 passed, 3 skipped, 0 failed** (con Docling y RapidOCR ya ausentes del entorno). Frontend 281 passed, `tsc` limpio. **Medición para D.4**: app en reposo 627 MB, pico 968 MB con un PDF de 40 páginas; el que manda ya no es Docling sino `torch`+`transformers`+`sentence-transformers`, que están por los modelos locales y no por la extracción — hacerlos extra opcional queda anotado como candidato en D.4 | ⏳ **Pendiente, va ANTES de Deploy**. Decisión en `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` (2026-08-10). Separa dos cosas que se llamaban igual: al **corpus** solo entra `.md` conforme al contrato —lo convierte el pipeline de curación, que vive fuera y previsiblemente pasará a plantilla + pandoc—, y el **contexto temporal** (PDF que alguien aporta para preguntar, o fuente de un informe) se extrae con **pdfplumber**, que ya es dependencia directa. EXT.1 cierra la puerta del corpus, EXT.2 sustituye Docling por pdfplumber en las dos vías de contexto **con guarda de documento escaneado —que debe fallar en alto, no ingerir un documento vacío—**, EXT.3 retira Docling del árbol y **mide la huella**, que es lo que dimensiona la VM en D.4. El OCR no se pierde: ya vive en la curación, con `origen_del_text` para declararlo |
| Deploy GCP | — | **D.0** | Sonnet | ⏳ Pendiente, y **ya no es lo siguiente**: el 2026-08-22 el usuario lo movió DETRÁS de PLAT e IDE —«no tiene sentido hacer el deploy de una aplicación con una estructura y unos mecanismos de identificación que no son los que se van a utilizar»—. **Tarea nueva heredada de IDE.1**: el inventario de variables de entorno tiene que incluir el ajuste de la autoridad del rol. **D.4.0 añadido el 2026-08-11**: `torch`, `transformers` y `sentence-transformers` pasan a un extra de instalación `[local-models]`, con importación perezosa y un error que diga cómo instalarlo. Están solo por `LocalEmbeddingService` y `LocalReranker`, así que con embeddings de Vertex no se usan pero se pagan enteros (216+172 MB y casi todo el arranque, medido en EXT.3). **Va antes de D.4-VM**: cambia el tamaño de la máquina de ~2 GB a ~150-250 MB esperados, y ese es el número que D.4 fija. No retira capacidad: el modo edge instala el extra. **BLOQUE REESCRITO EL 2026-08-10: el destino es una VM, no Cloud Run** (`docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2). El planificador de calidad es un APScheduler del `lifespan` y el rastreo va por `BackgroundTasks`: con escalado a cero el primero no dispara y el segundo muere a media ejecución, y el descuento que justificaba Cloud Run no era cobrable porque el scheduler exige CPU continua igual. VM + `docker-compose.prod.yml`, con **Cloud SQL y GCS** conservados —el estado sigue gestionado—. **D.1 ya está hecho**: lo resolvió SEC.8.5 con `HubWidgetKey`, que es superconjunto de la API key que D.1 describía (hash, revocable, solo abre `public_anon`). **D.4 y D.5 reescritos** (una máquina en vez de tres servicios Cloud Run: `embedding-service` y `docling-service` desaparecen por MOD.2 y EXT.3) y **D.6 nuevo** (copias con restauración probada, vigilancia, y la guía de incrustación del widget que D.1 dejó suelta). **Desaparece como problema** el ejecutor de trabajos que SEC.8.8 aplazó: en una VM el proceso vive |
| **RAG.6b** — Adaptador de Vertex para el reranker + medición del valenciano | — | RAG.6b | Opus | ⏳ **Pendiente, y va DESPUÉS del bloque Deploy** (decisión 2026-08-01). El Ranking API vive en Discovery Engine y lo habilita **D.0**, así que este prompt no puede cerrarse antes. Comprueba que el contrato escrito coincide con el real —un adaptador probado solo contra un doble está verificado en su lógica, no en su integración— y decide con el gate de RAG.1 sobre el dorado en valenciano si el flag se enciende en algún sitio. **No depende del corpus v1**: el dorado ya está en valenciano y el corpus de fixture son 25 normas breves. Modelo cerrado: `semantic-ranker-default-004` (1.024 tokens; las variantes de 512 truncarían la mitad de cada chunk). Riesgo abierto: Google declara 25 idiomas y no publica cuáles; el catalán no aparece |
| **Bloque FAQ** — Preguntas frecuentes como contenido citable | FAQ.2 ✅ | — | — | ✅ **Completo (2026-08-11)** — FAQ.1 (`1dd4910`) formato y validación, FAQ.2 autoridad de la cita. **Suite backend: 1819 passed, 3 skipped, 0 failed.** Dos hallazgos del RED: el troceador **ya** hacía lo correcto con encabezados y anclas (no hubo que tocarlo), y el "regalo gratis" de sembrar el dorado desde la FAQ **no era gratis** — la entrada resultaría circular, porque el documento que contiene la frase la recupera siempre; queda descartado y explicado en el plan. `content_class` viaja ahora del documento al fragmento y de ahí a la evidencia, con el aviso **dentro** del texto que ve el modelo  ⏳ **Pendiente, añadido el 2026-08-11**. Se ingieren como documentos con `content_class: faq` —valor que el contrato ya admite—, no como ejemplos en el prompt (no escala, e invita a parafrasear una respuesta redactada con cuidado) ni como dataset dorado (eso mide recuperación, es artefacto de prueba). La razón de fondo: **el texto de la pregunta es un objetivo de embedding casi perfecto**, porque se parece a lo que el ciudadano escribe mucho más que el artículo que la fundamenta. FAQ.1 fija el formato —**un encabezado por pregunta**, con ancla `{#faq-N}`, para que pregunta y respuesta caigan en el mismo fragmento; con negritas o listas, un corte deja media pregunta con la respuesta de otra y eso se cita mal sin que se note—. FAQ.2 cierra el riesgo real: **una respuesta sugerida no es una norma**, y tiene que citarse como orientativa con enlace a la norma que la sostiene. De regalo, el mismo fichero siembra el dorado y alimenta el detector de huecos |
| **Bloque REV** — Revisión humana de las respuestas del asistente interno | — | REV.1 | Sonnet | ⏳ **Pendiente, añadido el 2026-08-11**. Gerencia quiere un asistente para funcionarios **con identificación** y poder **revisar las respuestas** para valorar si son adecuadas o si conviene reformular las FAQ. Se evaluó OWUI para esto y se descartó: es una interfaz de chat y **no aporta la revisión**, que es lo que se pide. **Casi todo existe ya**: el asistente restringido es configuración (`access_mode: restricted` + `allowed_saml_groups` de SEC.2.1 sobre el SSO de AUTH), cada turno queda en `HubInteraction`, la pantalla de revisión con CSV es `ReportsPage` sobre `/hub/feedback/{id}/review`, y el bucle al contenido lo hace el detector de huecos de RAG.14. **REV.1** añade lo que falta: el veredicto de quien revisa sobre conversaciones **reales** (hoy `feedback_score` es del usuario final), replicando el patrón `verdict`/`verdict_note`/`verdict_by` que RAG.13 ya usa en escenarios de prueba, con cola de pendientes y nota obligatoria cuando el veredicto es «mal». **REV.2 es CONDICIONAL** —hilos de conversación persistentes, lo único que OWUI habría dado hecho— y solo se ejecuta si el piloto muestra que los funcionarios lo piden |
| Bloque OWUI — Carcasa de chat desechable (adaptador compatible-OpenAI + Pipe) | — | ❌ | — | ❌ **DESCARTADO el 2026-08-11** (decisión del usuario). **Reconsiderado el mismo día** con el caso de Gerencia (asistente interno revisable) y **confirmado el descarte**: OWUI no aporta la revisión, duplicaría el registro de conversaciones y debilitaría la cadena de identidad. Lo que sí daba hecho —hilos persistentes— queda como REV.2 condicional. Se reabriría solo si Gerencia quiere un espacio de trabajo conversacional (hilos largos, adjuntos, prompts guardados, compartir) y no un asistente de preguntas con fuente. Cuatro razones: se pierde la identidad institucional —que SEC.8.6 y el hallazgo #3 de MAN.2 acaban de construir—, actualizar OWUI cuesta, consume recursos de la VM única, y el público al que servía (personal interno, con historial y UX rica) ya está servido o es más barato de añadir al frontend propio. **El adaptador compatible-OpenAI también se aparca**: tiene valor independiente, pero solo si aparece un consumidor concreto; sin él es código especulativo. El andamiaje (scope `chat:completions`, PAT, identidad delegada) ya está desde SEC.2.1 si algún día se reabre. Lo que se pierde, dicho sin adornos: historial de conversaciones y UX de chat rica. Registro original abajo. ~~Pendiente — OWUI.1-OWUI.3 (post-deploy). Añadido 2026-07-24 desde `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md`.~~ Adaptador `/v1/chat/completions`+`/v1/models` sobre el grafo, contrato de citas P6 + anonimización P7, Pipe delgado. Reglas: OWUI llama al backend, la gobernanza no vive en OWUI. **Ampliado 2026-07-27**: `/v1/models` filtrado por `assert_chatbot_access`, cabecera `X-GovGenAI-Actor` firmada emitida por el Pipe (decisión (a)), traducción de 429/403 a errores OpenAI, y sección obligatoria "Lo que NO se usa de OWUI" (ni Groups para autorizar, ni LiteLLM, ni plugins de token-tracking) |
| Bloque ING.0 — Fundamentos del corpus normativo | ING.0.5 ✅ | — | — | ✅ Completo — **replanificado 2026-07-28**: de 2 prompts a **5** (ING.0.1 vocabulario como dato, ING.0.2 modelo de datos del documento, ING.0.3 front-matter + manifiesto, ING.0.4 chunker 5 niveles + anclas, **ING.0.5 Opus** reconciliador + CLI). Los antiguos ING.0.1/ING.0.2 (nunca ejecutados) quedan sustituidos; su contenido se conserva ampliado en ING.0.3 e ING.0.5. Motivo en el historial 2026-07-28 |
| Bloque VIS — Vistas del fundamento único (recuperación por metadatos) | VIS.3 ✅ | — | — | ✅ Completo — VIS.1 (filtro de metadatos en SQL, fail-closed) + VIS.2 (Niveles 0/1/2: índice de submaterias, selección escalonada, inyección de subconjunto con recorte) + VIS.3 (canónica única, derogados fuera de la recuperación, advertencia de vigencia garantizada por el grafo). Detalle en el historial 2026-07-31 |
| **Bloque DET** — Desempate determinista del retriever | DET.1 ✅ | — | — | ✅ Completo — **añadido y ejecutado el 2026-08-02** al cuadrar la deuda del cierre de RAG. El orden de dos fragmentos empatados lo decidía el plan de la consulta, o sea que decidía **qué norma se cita**. Desempate por `content_hash` (no por `id`, que es uuid4 y cambia en cada reingesta): **en SQL en la rama léxica**, **en Python tras el LIMIT en la vectorial**, porque un `ORDER BY embedding <=> $1, id` **inutiliza el índice HNSW** de RAG.3 (medido: pasa a `Seq Scan + Sort`). 5 tests nuevos, baseline regenerada y ya estable |
| Bloque SYNC — Sostenibilidad de la vigencia del corpus | SYNC.2 ✅ | — | — | ✅ **Completo (2026-08-02)** — SYNC.1 (fuente MCP sobre el reconciliador de ING.0.5, con `content_hash` de transporte para que el coste sea proporcional a los cambios) + SYNC.2 (caducidad activa: `data_revisio_prevista` vencida ⇒ finding `revisio_vencuda`, con default de 1 año al ingerir). Suite completa **1500 passed, 1 skipped, 0 failed**. Detalle en el historial. ~~planificado 2026-07-28~~ |
| Bloque TST — Fiabilidad de la suite de tests | TST.4 ✅ | — | — | ✅ Completo — **TST.4 añadido el 2026-08-01** (coste de la verificación: sin cobertura por defecto, `-n auto`, BD por `TEMPLATE`; política escalonada en CLAUDE.md). TST.1 (mocks sobre la clase, no el event_loop) + TST.2 (BD desechable en e2e/auth/pipeline, residuos limpiados) + TST.3 (cero rojos preexistentes). 4 guardarraíles en `tests/infra/test_suite_hygiene.py`. Detalle en historial 2026-07-30 |
| Bloque MOD — Modelos de embedding y reranker: local en edge, API en cloud | MOD.2 ✅ | — | — | ✅ Completo — **añadido el 2026-08-01** a petición del usuario, antes de RAG.6 y **antes de cargar el corpus v1**. Decisión en `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`. 2 prompts: ~~MOD.1 propósito en la configuración + procedencia en el vector~~ ✅, MOD.2 selección del servicio por la cascada (`get_embedding_service` deja de devolver el local a pelo; `HttpEmbeddingService` para el microservicio) |
| Bloque RAG — Refuerzo del retrieval y calidad RAG | RAG.14 ✅ | — | — | ✅ **Completo (2026-08-02)** — planificado 2026-07-15 desde `docs/COMPARATIVA_RAG_LAMB.md`. 14 prompts (RAG.1-RAG.14), 13 ejecutados aquí + RAG.6b fuera del bloque: ~~dataset dorado+CI~~ ✅, ~~consolidación de grafos~~ ✅, ~~HNSW~~ ✅, ~~tsvector~~ ✅, ~~umbral+presupuesto~~ ✅, **reranker RAG.6 → partido en 6a/6b el 2026-08-01**, ~~contextual retrieval~~ ✅, ~~parent-child~~ ✅, ~~metadato embeddings~~ ✅, ~~query rewriting~~ ✅, ~~bypass~~ ✅, ~~progreso jobs~~ ✅, ~~test scenarios~~ ✅, ~~feedback→huecos~~ ✅. **RAG.6b salió de este bloque y va detrás de Deploy** —ver su fila propia—. RAG.9 llegó muy solapado con MOD.1 y se redujo a hacer obligatoria la procedencia, poner la guarda en la consulta y escribir la CLI |

| **Bloque PIL** — Los dos asistentes del piloto: Vertex, corpus real y pruebas en local | PIL.7 ✅ | — | — | ✅ **Completo (2026-08-15)** — los 7 prompts. Adaptador de Vertex con lote y propósito del embedding, borrado de chatbot con su corpus, aviso de vigencia desplazada, vocabulario y validación, los dos asistentes creados, **37.504 fragmentos ingeridos** y calibración medida. **Suite backend completa: 1921 passed, 3 skipped, 0 failed.** Migración `a1p2i3l4m5n6` aplicada. **Tres hallazgos abiertos que no se arreglan aquí**: la rama léxica devuelve 0 resultados para preguntas naturales (`websearch_to_tsquery` exige TODOS los términos), las cuotas de SEC.4 no tienen superficie, y la página de documentos bloquea el navegador con 297 documentos | ⏳ **Pendiente, planificado el 2026-08-15.** Análisis en `docs/PLAN_CHATBOTS_E_INGESTA_LOCAL.md` (reescrito el mismo día: la versión del 08-11 daba por pendiente lo que ya está hecho y por resuelto lo único que no). 7 prompts. **Cuatro decisiones del usuario**: embeddings por **Vertex con adaptador propio** (es el proveedor del despliegue y el corpus se embebe una vez), Gerencia como `authenticated` en local y `restricted`+SAML al desplegar, el borrado de chatbot **se arregla en código**, y el aviso de vigencia desplazada **entra antes** de las pruebas. **Cuatro hallazgos verificados contra el código**: el corpus ya viene desdoblado en dos paquetes listos (`generat/ingesta/normatiu` 298 `.md` / `gerencia` 124) con `ambit_principal`+`submateries` en campos reales, así que `assert_vocabulary` **ya no pasa trivialmente y aborta la ingesta** sin vocabulario cargado; **no existe adaptador de Vertex** (`GoogleEmbeddingService` es la API de AI Studio y el resolver solo conoce `google_genai`/`local`); **ningún adaptador por API expone `embed_batch`**, así que el watcher haría ~21.400 llamadas de una en una; y **`hub_documents.chatbot_id` no tiene FK**, así que borrar un chatbot deja su corpus huérfano. Más un defecto del corpus que se resuelve de nuestro lado: de 86 unidades desplazadas por los Estatutos de 2025, **83 tienen fragmentos sin la nota de vigencia**, y se hidrata al montar la evidencia |
| **Bloque PRO** — Las puertas al LLM del módulo de Informes, con el legacy delante | PRO.9 ✅ | — | — | ✅ **Completo (2026-08-17)** — nueve prompts + PRO.2.1. **Reabierto el mismo día con dos prompts más, antes de las pruebas manuales**, a petición del usuario: **PRO.8** (gráficos deterministas) y **PRO.9** (lo que el ETL necesita para una hoja de cálculo). El criterio del usuario es el mismo en los dos casos y es correcto: «los más usuales se elegían de forma determinista sin tener que programarlos». Al medirlo, mi razón para dejarlos fuera en PRO.5 estaba incompleta —juzgué «tipos que nadie ha pedido» sin comprobar cuál es la alternativa cuando faltan, y la alternativa es **generar código**: `translate_nl_to_config("chart_config")` no devuelve configuración, llama a `generate_script()`, y una plantilla **no puede ni pedir un título**—. En ETL la comprobación dio lo contrario de lo esperado: **lo determinista del legacy está portado al 100%** en PRO.4, así que ahí no hay migración pendiente; lo que falta es cobertura de cuatro operaciones que **ni el legacy ni nosotros** teníamos y que una hoja real necesita —columna calculada, números en formato español leídos como texto (esta es la peor: `sum()` sobre texto **concatena, sin error**), ordenar y unpivot—. Los 7 prompts anteriores + **PRO.2.1 añadido a mitad de bloque** a petición del usuario (biblioteca de prompts con el tier sobreescribible). **Suite backend completa: 2197 passed, 3 skipped, 0 fallos** (11 m 42 s desde Git Bash); frontend sin fallos; `tsc` limpio; dos migraciones aplicadas (`c3v4y5z6a7b8` veredicto del auditor, `d4w5z6a7b8c9` prompts de actividad). **El resumen del bloque, en una línea: las puertas al LLM estaban cerradas y detrás de ellas el camino estaba cortado en once sitios.** Lo cerrado: auditoría de tres niveles con rutas absolutas y dos listas (PRO.1); nivel 2 escribe y nivel 3 audita, con el veredicto del modelo encima de la determinista (PRO.2); el prompt y el nivel de cada actividad editables desde el panel (PRO.2.1); el script aprobado extrayendo dentro de un informe (PRO.3); ETL con modelo y las diez operaciones de limpieza del legacy (PRO.4); gráficos en el informe y el informe **descargable** (PRO.5); el copiloto alcanzable y respondiendo con citas (PRO.6). Lo que se descubrió y nadie sabía: **el fichero de prueba no llegaba nunca al sandbox**, **los datos extraídos no se veían en ningún informe** —ni por script, ni por Excel, ni por PDF—, **el bloque CHART no dibujaba nada**, **el informe no se podía exportar** y **`blocks/handlers.py` sólo lo importaban los tests**. Comparativas escritas en `docs/COMPARATIVA_LEGACY_INFORMES.md` y `docs/COMPARATIVA_ETL_LEGACY.md`; niveles de modelo en `docs/NIVELES_DE_MODELO.md`. Planificado el mismo día: ⏳ 7 prompts. Planificado y **reescrito el mismo día** al avisar el usuario de que todo esto ya estaba programado, probado y funcionando en NiceGUI (`C:\Users\fabra\Documents\AutomatIA`). Lo que iba a ser «cablear dos dependencias» pasa a ser **portar decisiones ya tomadas**, y varias son mejores que las del código nuevo: el legacy tiene auditoría determinista de **tres niveles** (`SAFE`/`WARNING`/`CRITICAL`) con número de línea y **regex de rutas absolutas** que la nueva perdió —un script que abra `C:\Users\...` pasa su auditoría—, mientras la nueva es binaria (`approved = not findings`) y un `import csv` tumba la propuesta igual que un `eval()`. Además: **el nodo ETL del grafo se construye sin modelo** (VER.1 no le pasó `etl_llm`) y **no hay endpoint de ETL**, siendo ETL y gráficos lo que el usuario señala como más usado; el copiloto y el modo foco **estaban montados en el legacy**, así que no hay que decidir dónde van. Decisiones: auditoría graduada, **Tier 2 para escribir y Tier 3 para auditar** (hoy todas las configuraciones son de nivel 1), auditoría con modelo **encima** de la determinista y no en su lugar, y comparar con el legacy antes de escribir en ETL y extracción de PDF. **Los scripts libres se aparcan para automatizaciones**, razonado en el bloque |
| **Bloque RAS** — Rastreo de un portal institucional real | RAS.5 ✅ | — | — | ✅ **Completo (2026-08-18)** — los 5 prompts. **RAS.1** cortesía (pausa por host, `robots.txt` una vez por host con su `Crawl-delay`, User-Agent con contacto, presupuesto de tiempo, concurrencia acotada) y, de paso, **un rastreo truncado ya no declara bajas**: las bajas se calculaban como «activas que no aparecen», lo que con `max_pages` declaraba desaparecido lo no visitado. **RAS.2** `needs_javascript` en vez de acusar de vacía, con heurísticas **calibradas contra el portal** —una página estática de `www.uji.es` lleva `<noscript>` y diez `<script>`, así que ni eso es evidencia— y, por el camino, de una página se guarda **su texto y no 51 KB de marcado** (con el HTML dentro, `token_count` medía plantillas, el umbral de `thin` era inalcanzable, el detector semántico comparaba menús idénticos y al corpus llegaban `<div>`). **RAS.3** reanudación por cola guardada, reintentos con espera creciente, 404 ≠ timeout en severidad, y **no pedir dos veces la misma página** (el recorrido descargaba y tiraba; el guardado volvía a pedir: 25 páginas, 50 peticiones). **RAS.4** decisión escrita **sin navegador**, con la medición delante: 0 de 25 páginas lo necesitan. **RAS.5** el apartado de la Escuela de Doctorado de punta a punta, y aquí salieron **siete defectos más**, tres que impedían rastrear y cuatro que hacían mentir al informe: un enlace roto tumbaba el rastreo completo (primer intento real: **cero páginas** por un 404), un PDF enlazado se guardaba como texto y el byte `0x00` lo tumbaba otra vez, `config_json` no se podía fijar ni al crear ni al editar un sitio —así que `url_regex_filter`, la decisión operativa del bloque, era inalcanzable desde la interfaz—, la mitad de las páginas eran la misma en `http` y en `https` (191 supersesiones falsas), el portal tiene una **trampa de rastreador** en su conmutador de idioma (526 URLs pendientes que no acababan y 107 supersesiones falsas más), los 404 salían además como `empty` crítico, y una página ilegible se declaraba «la versión vigente». Y en el camino al asistente: **el botón de ingerir respondía 202 y no ingería nada** (servicio sin watcher, fallo en background), **`changed_page_ids` no lo consumía nadie** (el portal cambiaba y el asistente seguía citando el texto viejo) y **el job del arranque se construía con `watcher=None`**, así que nada de eso podía ocurrir en la aplicación real. Decisión del usuario: una página del corpus que cambia **se actualiza sola y queda avisada** (`content_updated`). Caso escrito en `docs/CASO_CURACION_ESCOLA_DOCTORAT.md`; decisión de renderizado en `docs/DECISION_RENDERIZADO_RASTREO.md`. Planificado el mismo día: ⏳ **Pendiente, planificado el 2026-08-18.** Caso guía: **el apartado de la Escuela de Doctorado de `www.uji.es`**, elegido porque está acotado, su contenido envejece de verdad y **es la misma unidad que el caso del Bloque SEG** —la misma gente, dos herramientas—. **La finalidad ya está construida y no se toca**: los detectores emiten `empty`, `thin`, `stale`, `orphan_page`, `crawl_error` y **`superseded`** (agrupa versiones del mismo recurso quitando los segmentos de año de la URL, que es literalmente «la nueva se publicó y la vieja sigue ahí»), más duplicado y contradicción por semántica; y `CorpusSelectionService` ya lleva de la página rastreada al corpus del asistente con decisión humana. **Lo que falta es poder apuntarlo a un portal de verdad**, y son cuatro cosas. (1) **Cortesía**: el bucle es secuencial, con `timeout` de 10 s y **sin pausa entre peticiones ni lectura de `robots.txt`** — miles de peticiones seguidas contra el portal de la propia casa figuran en sus registros como lo que parecen; es requisito, no mejora. (2) **El contenido dinámico**, que el usuario señaló: los enlaces se extraen con una regex sobre `href=`, así que una página pintada con JavaScript vuelve sin texto y el detector emite hoy **`empty` con severidad crítica** — un falso positivo que afirma lo contrario de la verdad y que arruinaría la credibilidad del informe en la primera pasada. Se resuelve con **sondeo previo sin navegador** (la señal más fuerte sale gratis: el hueco entre las URLs del sitemap y las que alcanza el recorrido por enlaces) y con un tipo nuevo **`needs_javascript`**, que dice lo único que el sistema sabe de verdad: «no se ha podido leer sin renderizar». (3) **Reanudación**: la cola BFS vive en memoria y arranca siempre de `root_url`; un corte en la página 8.000 obliga a empezar de cero. Y un `timeout` se convierte hoy en `crawl_error` crítico sin reintentos, o sea decenas de falsos positivos por causas de red. (4) **Renderizado con navegador, sólo si el sondeo dice que hace falta**, y como extra de instalación desactivado por defecto: es la misma decisión que se tomó con `torch` y la app está en ~345 MB precisamente por eso. **Fraccionar, no rastrear el portal entero**: el spider ya lee `url_regex_filter`, así que se da de alta un sitio por apartado — y no es sólo técnico, cada apartado tiene un responsable distinto y un informe del portal completo no lo lee nadie |
| **Bloque SEG** — El asistente de informes de seguimiento: valoración anclada a su tabla | SEG.5 ✅ | — | — | ✅ **Completo (2026-08-18)** — los 5 prompts. **Suite backend completa desde Git Bash: 2360 passed, 3 skipped, 0 fallos** (8 m 38 s); **frontend: 358 passed, 0 fallos**; `tsc` limpio; el contrato OpenAPI no cambia. Verificado de punta a punta con el informe real del Programa de Doctorado en Ciencias (70.181 bytes, 42 tablas): cada apartado trae **una** tabla y es la suya, ninguna valoración usa cifras que no estén en el origen, las tres tablas con «No hay valor» lo dicen, y el DOCX sale con las tablas como tablas de Word. Caso escrito en `docs/CASO_INFORME_SEGUIMIENTO.md`. **Montarlo de verdad destapó cuatro cosas más, todas del mismo tipo —la capacidad existía y la puerta estaba cerrada—**: (1) **los bloques `TABLE` no los pintaba nadie**, estaban en el contrato, el validador les exigía `data_block_ref` y el prompt los ofrecía, pero ningún nodo los rellenaba, así que el informe salía con las nueve tablas vacías sin error ni aviso —es el mismo agujero que PRO.5 tapó para los gráficos, y lo cubre ahora `TableRenderNode`—; (2) **un bloque que no está en ninguna sección desaparece del informe**, porque la vista previa y el ensamblado recorren `sections[].block_ids`, y el informe salía corto con aspecto de estar bien —ahora se rechaza al publicar la plantilla y al validar el borrador, con la regla también en el prompt—; (3) **las tablas del cuerpo se pintaban sin estilo**, porque sólo estaba vestido el anexo de auditoría (hasta ahora ningún bloque del cuerpo había producido una tabla); (4) **la valoración llegaba con markdown crudo** —`**Producción vegetal:**` impreso literalmente— y con longitud de ensayo. Planificado el mismo día: ⏳ **Pendiente, planificado el 2026-08-18.** Es el **supuesto de uso que el usuario necesita y que no estaba escrito en ningún plan**: «el informe lee la información, presenta las tablas y gráficos en la estructura que define la plantilla de forma determinista y, a continuación, la literatura con la valoración de tendencias o el resumen de resultados la propone la IA, sujeto a aprobación o edición por el humano». Caso guía real: el **informe anual de seguimiento de un programa de doctorado**, con dos documentos sobre la mesa —el resumen de datos de un programa (30 tablas) y el prompt de la gema de Gemini que se usó antes—. **Por qué el intento anterior no bastó**: la gema *inventaba datos al pintar las tablas* y *resumía omitiendo información relevante*; su prompt pelea contra eso en mayúsculas, y perder esa batalla a base de instrucciones es lo esperable. Aquí las tablas **no las escribe el modelo**. **El hueco que decide si el módulo sirve para esto**: `_build_context` mete **todos** los bloques extraídos en un solo contexto y lo entrega igual a cada apartado de IA, y `AIAssistedTextBlock` sólo tiene `ai_prompt_template_id` y `review_policy_id` —**no puede decir «reflexiona sobre la Tabla 1.2»**—, así que con 30 tablas cada valoración recibiría las 30: el fallo de la gema reproducido por arquitectura. Sin SEG.1 el resto no vale. 5 prompts: SEG.1 anclaje (`data_block_refs`, contexto sólo con esos bloques, y un apartado sin anclaje **consta en el manifiesto**), SEG.2 la instrucción de valorar tendencias con sus reglas duras portadas del prompt real (no recalcula, «No hay valor» se respeta, sugerencias en tono no imperativo), SEG.3 pipeline de tablas Markdown (el origen de hoy; JSON o API mañana, aditivo), SEG.4 **cablear la edición**, que el backend ya sabe hacer —`editBlock` guarda el original en auditoría y **su hook generado no lo llama ninguna pantalla**—, SEG.5 la plantilla del informe de doctorado de punta a punta con datos reales. **Decisión tomada al planificar**: los datos que no están en el documento se piden **por formulario y no por conversación** —cada respuesta queda registrada y asociada al informe—, con campos opcionales y selector sí/no, **sin condicionalidad**, que exigiría ampliar el contrato de entrada sin aportar nada que un campo vacío no resuelva |
| **Bloque CUR** — La curación vista por quien cura | CUR.9 ✅ | — | — | ✅ **Completo (2026-08-19)** — los 7 prompts + CUR.2.1 + **CUR.8** (cuatro arreglos de las pruebas manuales: las dos URLs de un duplicado, la razón de cada hallazgo, la confirmación de la ingesta y el botón de PDF sólo cuando hay PDF) + **CUR.9** (la reconciliación: un hallazgo que ya no se detecta se retira, y la cola arranca en «Pendientes»). CUR.1 ✅ la fecha real que publica el portal (`.clockBarDate` → `24/09/2025` \| `Escola de Doctorat`) con selector **por sitio**: 28 de 31 páginas del apartado traen ya fecha real, y salen páginas de 2015 y 2017 con su unidad responsable. CUR.2 ✅ una serie anual es **un** hallazgo informativo con sus URLs y fechas, y ninguna página aparece en dos apartados; más el duplicado exacto por `content_hash` con las dos URLs y sus dos fechas, que pidió el usuario. **CUR.2.1 ✅ añadido a mitad de bloque** por una pregunta suya sobre el despliegue multiorganización, y tenía razón: el aislamiento de datos sí era por organización, pero **los criterios de juicio eran globales** —`stale_days` y el umbral de contenido pobre los ponía el constructor del detector y **nadie los pasaba**, y CUR.2 acababa de fijar global que una serie por años no supersede, que es cierto en la UJI y falso en un portal que versiona convocatorias—. Ahora `stale_days`, `thin_min_tokens` y `version_series_policy` (`series`\|`superseded`\|`off`) son configuración del sitio, con los defectos de hoy; frontera escrita en `docs/CURACION_MULTIORGANIZACION.md`: **el criterio es dato, la honestidad es código** —la cortesía, no acusar de lo que no se pudo leer, 404 ≠ timeout y la identidad de una URL no se pueden desactivar—. **CUR.3 ✅** al corpus sólo el contenido, y la medición corrigió dos veces al plan: el portal **no usa `<nav>` ni `<header>`** —su menú son `div` con clases— pero **sí `<main>`**, que es la señal inversa y quita el 39 % de una página y el 67 % de la de normativa; y la regla de seguridad planificada («si se lleva más de la mitad, conserva el original») **habría revertido justo esa página**, así que se cambió por lo único inequívoco: quedarse sin nada. Con selector de contenido, selectores de plantilla declarados y una pasada de **repetición medida** —una línea que sale en el 60 % de las páginas es menú—, el rastreo completo dio **349 páginas, 21 bloques de plantilla, 176.303 caracteres quitados, 0 revertidos y 0 páginas vacías**: de 4.106 caracteres por página a 1.585. **CUR.4 ✅** poder mirar lo que el informe dice: las URLs de los hallazgos son enlaces que abren en otra pestaña, un hallazgo de grupo **se despliega** con sus versiones y sus fechas en vez del «+4 más» muerto, el «+N más» del informe de auditoría también, y —lo que más falta hacía y no estaba pedido así— se puede **leer el texto guardado** de una página, que es lo que iría al asistente y lo único que permite juzgar si un hallazgo es cierto y si el recorte de CUR.3 se comió algo. Y verificarlo en el navegador destapó que **la pantalla no tenía con qué**: el contrato de la cola de hallazgos no servía `page_id` ni la señal, así que los dos botones nuevos no aparecían nunca fuera de los tests —275 hallazgos reales en pantalla, cero botones—. Arreglado en el contrato (`_FindingOut` con `page_id` y `signal`), con el doble del test convertido en clase real: un `MagicMock` inventaba un `.signal` que la fila de la base de datos no tiene y habría dado el test por bueno leyendo un atributo inexistente. Verificado en vivo tras el arreglo: «Ver las 9 versiones» con sus fechas, 274 botones de ver texto, y el visor de una página mostrando `Acords Comité de Direcció … · Escola de Doctorat · 18/11/2021 · 263 tokens` con 1.052 caracteres de contenido limpio. **CUR.5 ✅** la descarga y la selección. La descarga era un `<a href download>` contra la API, o sea **una navegación sin cabecera de autorización**: 401, y el navegador enseñando su propio error —«el fitxer no es troba disponible»—, que no menciona el 401 y parece que el informe no exista. Ahora se pide con el cliente autenticado (`shared/api/download.ts`) y se entrega desde memoria, con el fallo visible en la pantalla si lo hay. **El mismo defecto estaba en Informes** —el `<a href>` a `/redaccion/workspaces/{id}/export`, con `Depends(get_current_user)` detrás—, así que PRO.5 dejó el informe «descargable» sin que la descarga pudiera funcionar: arreglado también, con su test. Y en publicación se puede **elegir**: casilla por página, «marcar todo», e ingerir sólo lo marcado —sigue sin haber «ingerir todo el sitio»: cada página entra porque alguien la marcó; lo que desaparece es pulsar 349 veces—. Además **se ve lo que ya está en el corpus**, que exigió una decisión de contrato: una página ingerida ya no se descarta de la lista, se devuelve con `is_ingested` —esconder la fila no distingue «ya está en el corpus» de «nunca fue candidata», y al pulsar «Ingerir» la fila desaparecía sin confirmar nada—. Verificado en vivo: DOCX descargado de verdad (39.746 bytes en Descargas, los mismos que sirve el endpoint), «Descargar PDF» guarda un `.docx` porque **el servidor declara el fallback sin LibreOffice** y el nombre del servidor manda (la honestidad de VER.7 llega hasta el fichero guardado), tres páginas marcadas e ingeridas de una tacada (3 documentos en la base) y el resumen pasando a «346 por publicar · 3 ya en el corpus» con sus tres casillas bloqueadas; la exportación de Informes, un DOCX de 36.648 bytes. **CUR.6 ✅** reconocimiento antes de rastrear: un sondeo que **no guarda nada** —ni el sitio hace falta que exista— y devuelve las URLs agrupadas por subapartado, el total, el CSV descargable y **cuánto tardaría el rastreo**, que es lo que responde «de golpe o por subapartados». La estimación sale de lo medido y de la cortesía real: `segundos_por_pagina` se mide en el sondeo y se le suma la pausa que el rastreo va a usar, porque estimar con la latencia del sondeo rápido daría minutos donde el rastreo tarda horas. Verificado contra el portal, y la primera pasada estaba mal: el sondeo usaba la **profundidad del formulario** (1) y devolvía 11 URLs de un apartado que tiene 349 —contestaba a otra pregunta—; el plan decía «profundidad y tope propios» y ahora baja 3 niveles. Con eso: **219 URLs desde 60 páginas pedidas**, aviso de truncado por `max_pages`, y «unos 11 min, a 3,1 s por página». Y un hallazgo del portal que nadie buscaba: el apartado más grande sale como **`estudis` con 188 URLs**, porque la misma sección es alcanzable bajo `/estudis/centres/escola-doctorat/` además de `/centres/escola-doctorat/` — dos prefijos para el mismo contenido, que es parte de la duplicación que el usuario veía. **CUR.7 ✅** el detector semántico corre de verdad: existía desde 9Q.4 con sus tests y el job se construía con un solo detector, así que `audit_semantic_scope='full'` no significaba nada. Cablearlo destapó **cuatro defectos más**: el job **no persiste** los hallazgos (los cuenta y calcula `quality_score`, pero guardarlos lo hace cada detector, y el semántico decía que era del job), el flag `run_semantic` **nunca se aplicaba** (se mira con `getattr(detector, "_is_semantic", False)` y ningún detector declaraba el atributo), casi se cablea el adaptador equivocado —`RedactorDeBloques` cumple el mismo protocolo pero entiende su primer argumento como el **id** de una plantilla, así que el juez habría recibido «esa plantilla no está en el catálogo» y contestado `unrelated` a todo—, y el detector **funcionaba exactamente una vez por sitio**: la segunda pasada falla con `float32 is not JSON serializable` porque los vectores de pgvector vuelven como numpy y la similitud va a un JSONB. **Ejecutado cuatro veces contra el apartado real** (349 páginas embebidas, tope de 25 pares), y cada pasada corrigió la anterior: 10 hallazgos y **los 10 el falso positivo que el usuario ya corrigió en CUR.2**, con otra sintaxis —el archivo de formación transversal publica una página por curso académico (`/23-24/`, `/24-25/`) y la identidad de serie sólo reconocía años de cuatro cifras, así que **el determinista tampoco los agrupaba**—; arreglado en la identidad, sirve a los dos detectores, y el semántico deja de pagar llamadas por pares de la misma serie. Quedaban 11, de los que 9 seguían siendo ediciones del mismo curso con la ruta reorganizada (`recerca/programacio-r` → `tecniques/programacio-r`), que ninguna regla de URL puede cazar: se resolvió **diciéndoselo al juez** —el dato del dominio de CUR.2, generalizado—. Resultado final: **13 hallazgos, 0 contradicciones, 13 duplicados**, y los cuatro primeros son lo que el usuario sospechaba: la misma página bajo dos rutas del portal (`/base/escola/normativa/acordacded/` vs `/escola-doctorat/normativa/acordacded/`, `/base/info-academica/…` vs `/info-academica/…`, `internalitzacio` vs `base/internacionalitzacio` —con la errata incluida—) y **`/base/calendari` contra `/base/calendari/`**, que no es duplicación del portal sino nuestra: la misma página rastreada dos veces por la barra final. Arreglado con una clave de identidad que **no cambia la URL que se pide** (hay servidores donde `/x/doc` existe y `/x/doc/` da 404). El alcance semántico se puede cambiar desde la fila del sitio, con `off` incluido |
| ~~**Bloque CUR** (planificado)~~ | — | CUR.1 | Sonnet (CUR.2 y CUR.3, Opus) | ⏳ **Pendiente, planificado el 2026-08-19** a partir de las **pruebas humanas del Bloque RAS**. Ocho observaciones del usuario sobre el informe del apartado de la Escuela de Doctorado, y ninguna es de estilo: cuatro son hallazgos falsos o duplicados, tres son cosas que **no se pueden hacer desde la interfaz** —ver el contenido de una página, abrir una URL, elegir qué se ingiere— y una es un botón que responde 401. **El hilo común: el módulo produce un informe y no da forma de comprobarlo.** Dos entradas que no se deducen del código: (1) el dato del dominio que tumba un detector —el portal publica acuerdos y actas **por año y todos siguen vigentes**, así que declarar «superada» la de 2017 afirma algo falso, y encima la misma página sale en dos apartados—; y (2) el regalo que estábamos ignorando: **cada página publica su fecha y su unidad responsable en el HTML** (`<div class="clockBarDate">` → `24/09/2025` \| `Escola de Doctorat`), con lo que «desactualizada» pasa de conjetura a dato. 7 prompts: CUR.1 la fecha real del portal (selector por sitio, no hardcodeado), CUR.2 una serie anual es **un** hallazgo informativo y nunca la misma página en dos apartados, CUR.3 fuera el menú y la plantilla para que al corpus vaya solo el contenido —lo que habilita el chatbot de prueba—, CUR.4 poder mirar lo que el informe dice (URLs clickables, «+4 más» desplegable, y **ver el texto guardado** de una página), CUR.5 la descarga con autorización y la selección de candidatas, CUR.6 reconocimiento previo del sitio con recuento por subapartado y CSV, CUR.7 cablear el **detector semántico**, que existe, está probado y no lo ejecuta nadie —el sitio está en `full` y no cambia nada—. **CUR.1 y CUR.3 cambian lo que se guarda**, así que exigen volver a rastrear el apartado (12 min) para ver el efecto |
| **Bloque LEG** — Retirada del legacy de prompts de AutomatIA | LEG.5 ✅ | — | — | ✅ **Completo (2026-08-19)** — los 5 prompts. **Suite backend completa: 2488 passed, 3 skipped, 0 fallos** (8 m 14 s) **y sin el flake** de `tests/test_prompts.py` que llevaba semanas inventariado. Migración `h8a9d0e1f2g3` aplicada. **LEG.1** los ocho prompts leídos antes de borrarlos (`docs/COMPARATIVA_PROMPTS_LEGACY.md`): el vivo gana en generación de scripts —genera las listas prohibidas del auditor en vez de escribirlas a mano, prohíbe rutas absolutas y declara el contrato de `result`—, y una regla del legacy **se descarta a propósito** («maneja excepciones con try/except» convierte un fallo visible en una tabla vacía que nadie revisa, y el auditor vivo dice lo contrario); **lo único que aporta** es la nomenclatura semántica, portada al prompt del ETL con su test, porque el modelo crea columnas y su nombre acaba impreso en la tabla de un informe; y lo que no tiene equivalente —clarificación previa, orquestación de flujos con prioridad LOCAL/ORGANIZATION/PARTNER/GLOBAL, disparadores independientes con suscripción, pasos `PLACEHOLDER`— queda **citado** para el bloque de automatizaciones en vez de conservarse como código muerto. **LEG.2** el arranque deja de sembrar en `extraction_service_config` y `system_prompt`: era la causa común de los dos síntomas —arranques fallidos en desarrollo y el flake—, porque el servidor escribía mientras la suite reinicializaba. **LEG.3** fuera el orquestador huérfano (0 % de cobertura, 220 líneas nunca ejecutadas) y guardarraíl que prohíbe **abrir sesión** sobre `server_engine`, no importarlo: hay un test-smoke legítimo que sólo comprueba que el motor existe, y un guardarraíl con falsos positivos se acaba desactivando. **LEG.4** dos clases de diecinueve fuera de `models.py` —el fichero se queda— y migración que borra las tablas; al escribirla salieron dos cosas: se llaman `extractionserviceconfig` y `systemprompt` **sin guiones bajos** (es el nombre que SQLModel deriva de la clase, y por escribirlos «bonitos» falló el primer intento) y va con `IF EXISTS` porque en esta base no estaban, al haberse creado el esquema con `create_all` y no con Alembic. **LEG.5** el `main.py` de la raíz (705 líneas de NiceGUI) a `_legacy_nicegui/`, `arranque.bat` sin la opción que lo lanzaba y comprobado que su comando levanta el servidor; el `grep -r` a cero destapó **dos consumidores más** que el plan no conocía —`client_app/main.py`, otro lanzador NiceGUI, y `client_app/tests/unit/test_watcher_migration.py`, que prueba las rutas del fichero movido—, y los dos van a cuarentena con su ruta relativa. Planificado el mismo día: ⏳ **Pendiente, planificado el 2026-08-18** — sale de una pregunta del usuario sobre unos logs de arranque, y **no es limpieza estética**: esta vía **escribe en la base de datos en cada arranque del servidor**, que es lo que colisiona con la suite cuando ambos corren a la vez. Dos síntomas ya observados con una sola causa: los arranques fallidos del log del 2026-08-17 y el flake de `tests/test_prompts.py`, que pasa aislado y falla en la suite paralela porque usa `server_engine` —la BD real del desarrollador— y siembra prompts. **Qué es**: ocho prompts de la época de AutomatIA (generador de scripts, clarificación por tipo de tarea, procesado con LLM, naming semántico, orquestador de flujos, metaprogramación) sembrados en `ExtractionServiceConfig` y `SystemPrompt`. **Por qué se puede retirar**: su único consumidor es `knowledge_orchestrator_service.py`, que **no lo importa nadie** —cero referencias en `server/`, **0 % de cobertura**, 68 líneas sin ejecutar—; los prompts vivos son `HubPromptTemplate` (por asistente) y `HubActivityPrompt` (por actividad), que no se tocan. 5 prompts: LEG.1 **comparar antes de borrar** (es la lección de PRO.1 y PRO.4: el legacy tenía decisiones mejores y se vieron al leerlo), LEG.2 cortar la siembra del arranque, LEG.3 el orquestador huérfano y el test, con guardarraíl contra tests que escriban en la BD del desarrollador, LEG.4 migración que borra las dos tablas, LEG.5 el `main.py` de la raíz a cuarentena. **Tres fronteras localizadas al planificar**: `AutomationLibrary` **se queda** (la usa `library_router`, vivo); `models.py` pierde **dos clases de diecinueve**, no el fichero; y **`arranque.bat` todavía ejecuta `uv run main.py`**, así que mover el lanzador sin tocar el script deja un arranque roto |
| **Bloque VER** — Verificación de Informes y Curación antes del despliegue | VER.9 ✅ | — | — | ✅ **Completo (2026-08-17)** — los 9 prompts. **19 hallazgos, todos arreglados con TDD**, y el resumen es que **el módulo de Informes no funcionaba de punta a punta**: el grafo no se ejecutaba, no había pantalla donde abrir un workspace, la subida de ficheros no se persistía, la extracción los buscaba en el disco en vez de por `StorageService`, las cuatro transiciones de bloque daban 500 y `resume` no reanudaba. En Curación, **el rastreo fallaba siempre** (`site.url` vs `root_url`) y el «PDF» del informe era un DOCX disfrazado. Verificado en vivo: informe generado desde un Excel real con el texto de IA citando las cifras extraídas, y los seis caminos recorridos. Planificado el mismo día: ⏳ **Planificado (2026-08-17)** — 9 prompts. Los dos módulos llegan al despliegue sin haberse recorrido nunca de una pieza, y al planificarlo apareció que **Informes no genera nada**: `POST /workspaces/{id}/run` transiciona el estado y devuelve un `run_id` sintético sin ejecutar el `DraftingCoreGraph`, que está construido entero (14 nodos) y solo necesita sus dependencias inyectadas; `llm-drafts/propose`, `scripts/propose` y `copilot/ask` son stubs 503. Curación sí está cableada (crawler, detectores y planificador se registran en el arranque). **Decisión del usuario**: cablear la generación (VER.1) y `llm-drafts` (VER.2) y luego recorrer los seis caminos en navegador (VER.3–VER.8); copiloto y propuesta de scripts por LLM quedan fuera, documentados. Cierre con la matriz de lo irreducible y el `.bat` humano (VER.9). El crawl de curación apunta al sitio local del corpus en `:4174`, no a `www.uji.es` |
| **Bloque INF** — El módulo de informes, utilizable de punta a punta | INF.10 ✅ | — | — | ✅ **Completo (2026-08-20)** — los 10 prompts, nacido de las pruebas humanas del usuario sobre los dos caminos del módulo, que no llegaban al final. ⏳ **Pendiente, planificado el 2026-08-20** desde las pruebas humanas del usuario sobre los dos caminos del módulo. **Ninguno de los dos llegó al final.** Trece observaciones, y las dos que importan no son de estilo: **(A)** `WorkspacePage.tsx` tiene dos disparadores de la generación y **uno se salta la subida de datos** (el botón azul destacado, líneas 137-147, frente al submit del contrato, líneas 85-100) — en el log no hay una sola petición de subida, y de ahí sale toda la cascada `Required input slot missing: 'datos'` → tablas sin datos → bloques de IA en error; la plantilla, comprobada en BD, **no tiene ningún defecto**. **(B)** `preview_builder.py:37-49` considera pendiente todo bloque de IA fuera de `{approved, locked}` y `AIBlockReviewPanel.tsx` solo el que está en `needs_review`: un bloque que **falló** cae en el hueco, así que el panel anunciaba «Todos los apartados aprobados» mientras la vista previa y la exportación devolvían 409 por esos mismos bloques, **sin ninguna acción que pulsar**. Es la regla maestra nº2 incumplida: el frontend calcula el estado en vez de recibirlo. Además, **una regresión respecto al legacy señalada por el usuario**: `propose` recibe solo `prompt_nl` y el legacy mandaba `columns`, `dtypes`, `row_count` y `df.head(3)` **anonimizados** (`etl_factory.py:146-200`); y **el prompt induce el error que el validador castiga** (`llm_spec_service.py:85` llama «table» a lo que debe ser un `DETERMINISTIC_DATA`). **Decisión de alcance del usuario (2026-08-20): el control de acceso se resuelve por módulos concedidos, no con un rol nuevo** — hoy no hay ninguno (`App.tsx:92` solo comprueba que hay sesión, cero `role ===` en la navegación, routers de `redaccion` con `get_current_user` a secas), así que cualquier trabajador con cuenta puede editar los chatbots institucionales; el rol `informer` no sirve, su contrato es supervisar respuestas de la IA. 10 prompts en `Plan_TDD_Fase1.md` §Bloque INF; INF.1-INF.3 son los que convierten «no puedo terminar» en «puedo terminar» |
| **Bloque NIC** — Retirada del legacy NiceGUI, con inventario antes de borrar | — | NIC.1 | Opus (NIC.1 y NIC.3; NIC.2 y NIC.4, Sonnet) | ⏳ **Pendiente, planificado el 2026-08-21** al revisar el repositorio para abrirlo. Medido: `client_app/` tiene **505 ficheros versionados y 96 importan NiceGUI** (87 en `app/ui`), cuando la regla de `CLAUDE.md` dice que ahí sólo debe vivir el agente de ejecución local (`rpa_executor.py`, `modules/rpa/`, `modules/watchers/`). **Nada en producción lo importa** —las 10 menciones en `server/` son comentarios de procedencia— y sólo hay **un import real**, en `shared/tests/test_security_unification.py:44`. No está en `docker-compose`, ni en el `Dockerfile`, ni en CI. Y la UI NiceGUI existe en **cuatro sitios**: `Documents\AutomatIA`, el bundle de GenGov, `client_app/app/ui` y `_legacy_nicegui/`. **NIC.1 no borra nada: cruza** qué está cubierto en `server/app/modules/automation/` + `frontend/src/`, porque borrar 87 ficheros a ojo es como se pierde una funcionalidad sin enterarse. NIC.5 lo ejecuta el usuario y cierra la Fase 1 |
| **Bloque PLAT** — La administración de la plataforma, separada de la de Chatbots | — | PLAT.1 | Sonnet (PLAT.1, .2, .5, .7) · Opus (PLAT.3, .4, .6) | ▶ **En curso. PLAT.1 ✅ y PLAT.2 ✅ (2026-08-22); siguen PLAT.3…PLAT.7 después del Bloque IDE.** Planificado el 2026-08-22 a propuesta del usuario. 7 prompts, **partidos en la ejecución**: PLAT.1 y PLAT.2 van ANTES del Bloque IDE —las pantallas de IDE.4 e IDE.5 cuelgan de `/plataforma`, la sección que crea PLAT.2— y PLAT.3…PLAT.7 después. Todo antes de Deploy. **No es solo reordenar el menú: el backend y el frontend ya se contradicen.** `hub_llm_configs_router` exige `require_module("plataforma")` y `App.tsx` monta esa pantalla bajo `<RutaDeModulo modulo="chatbots">`, así que hoy **quien tiene `chatbots` y no `plataforma` ve el tab «Modelos LLM» y recibe un 403**, y quien tiene `plataforma` no puede llegar a la única pantalla que ese módulo protege: el módulo existe en `MODULOS_INICIALES`, se puede conceder y **no abre nada** (se retiró del menú porque era un `PlaceholderPage`). Ocho hallazgos medidos, entre ellos: `tier` lo consumen Informes, Curación y Chatbots y `HubLLMConfig` no tiene `organizacion_id` —es global—; `OrganizacionRead` mezcla identidad, tema y **una docena de `default_*` de RAG**, que es por lo que la pantalla acabó bajo Chatbots; el `<textarea>` «Configuración de tema (JSON)» escribe `HubOrganizacion.theme_config` y **nadie lo lee** (la cascada resuelve desde `hub_themes`); `AIBrainPage` importa plantillas de prompt **y** configs LLM sin recurso propio; y no hay interfaz para conceder módulos —**esto último salió a un bloque propio (IDE)**: `HubModuleGrant` dice que «no hay una tabla de usuarios única» y su `subject_id` es un `uuid5` del claim del token, así que no se puede enumerar a quién concederlas—. **El criterio no se inventa**: `Deploy: cloud` es configuración de plataforma, `Deploy: edge` es operación de un módulo. **PLAT.1 no se puede saltar**: sin la migración de concesiones, PLAT.5 deja fuera a todo admin no-superadmin. **PLAT.1+PLAT.2 se pueden adelantar** —dos prompts, ningún contrato tocado— y arreglan por sí solos el 403; merece la pena si el piloto va a tener administradores que no sean superadmin. **Posición en la secuencia sin decidir**: propuesta, después de NIC y antes de REPO |
| **Bloque IDE** — Identidad y permisos: alta manual hoy, grupos del IdP mañana | — | IDE.1 | Opus (IDE.1, .2, .3, .5) · Sonnet (IDE.4) | ✅ **Completo (2026-08-22)** — los 5 prompts. Fue ANTES de Deploy (decisión del usuario, 2026-08-22), después de PLAT.1 y PLAT.2. Planificado el 2026-08-22 al preguntar el usuario dónde estaba prevista la gestión de usuarios. La respuesta era **en ningún sitio**: `grep` sobre `planificacion/` no encuentra nada en Fase 1, 2 ni 3. 5 prompts. **Lo que quiere el usuario**: dar usuarios con roles a mano y que el SSO solo identifique, y **en el futuro** que los permisos vengan del ERP por un atributo del IdP. **Medio mecanismo ya está construido**: `resolve_role` resuelve el rol desde la aserción con tres niveles (`SAML_ATTR_ROLE` → `SAML_GROUP_ROLE_MAP` → `SAML_DEFAULT_ROLE`), los grupos viajan en el claim `groups` del JWT, y **ya tienen consumidor en producción** —el modo `restricted` de un chatbot cruza `allowed_saml_groups`—. **Dos huecos exactos**: (1) `_provision_sso_user` hace `sso.role = role` **sin condición**, así que un rol puesto a mano lo pisa el siguiente inicio de sesión —no falta la pantalla, es que no serviría—; (2) `HubModuleGrant.subject_id` es siempre una persona. **La decisión que unifica ahora y futuro** (usuario, 2026-08-22): declarar **quién es la autoridad** del rol (aplicación o IdP) y que el sujeto de una concesión pueda ser **persona o grupo**, con la semántica de `assert_chatbot_access` —rol o grupo, y el vacío es «nadie», no «todos»—. **El grupo entra desde el principio, también en la interfaz** (decisión del usuario): dejarlo para después convierte el paso al ERP en una migración en vez de un cambio de pantalla. Dos cosas que el bloque **no** hace, a propósito: unificar las cuatro tablas de identidad (`user_to_uuid` está en la propiedad de los workspaces, en los PAT y en las concesiones, y `es_propietario` ya acepta las dos formas desde SEC.8.1 — merece bloque propio con inventario antes de tocar), y repartir un IdP entre varias organizaciones (`SAML_ORGANIZACION_ID` asocia el IdP a **una**). **Prerrequisito del usuario para IDE.5**: qué grupos declara hoy el IdP institucional y cuáles sirven para repartir módulos |
| **Bloque REPO** — Sustituir el repositorio de GitHub por uno sin objetos huérfanos | — | REPO.1 | — (lo ejecuta el usuario) | ⏳ **Pendiente, y va DESPUÉS de NIC.5 por decisión del usuario (2026-08-21)**: no tiene sentido montar el repositorio definitivo y acto seguido meterle la retirada de 500 ficheros de legacy. El historial se reescribió el 2026-08-21 para sacar `logs/` (45 volcados con datos de usuarios reales) y se forzó el push, así que los commits viejos quedaron **inalcanzables pero no borrados**: GitHub los sirve por URL de SHA hasta que recoge basura. Hay que hacerlo **antes de que exista el primer fork**. Inventariado lo que se pierde: 0 issues, 0 PRs, 0 releases, 0 tags, 0 webhooks, ningún secreto de Actions, sin protección de rama — sólo la fecha de creación y el historial de runs. Incluye REPO.2: borrar `cgm-remote-monitor` (fork sin trabajo propio) y `GenGov` (44 volcados; su clon local `Documents\AutomatIA` ya es el archivo). Pasos completos en `Plan_TDD_Fase1.md` §Bloque REPO |

## 👉 EMPEZAR AQUÍ EL PRÓXIMO DÍA (actualizado 2026-08-22, al mover PLAT e IDE delante del despliegue)

**Cursor actual: PLAT.3** (PLAT.1, PLAT.2 y el **Bloque IDE completo** ✅ el 2026-08-22; siguen PLAT.3…PLAT.7 y luego Deploy) (y de ahí a PLAT.2 → IDE.1…IDE.5 → PLAT.3…PLAT.7 → Deploy). El **Bloque INF quedó completo** el 2026-08-20 (los 10
prompts) y el 2026-08-21 se preparó el repositorio para abrirse: limpieza de la raíz, licencia,
gobernanza y DCO. Ese trabajo no es un bloque del plan y no mueve el cursor, pero deja dos bloques
nuevos (NIC y REPO) y un orden que no se puede invertir. El 2026-08-22 se planificaron otros dos —**PLAT** e
**IDE**— y el usuario los puso **delante del despliegue**, que es lo que mueve el cursor a PLAT.1.

**Modelo sugerido para el próximo prompt**: **Opus** para PLAT.3 (decide qué campo pertenece a qué ámbito y parte un DTO).

**IDE y PLAT van ANTES de Deploy** (decisión del usuario, 2026-08-22): «no tiene sentido hacer el deploy de una
aplicación con una estructura y unos mecanismos de identificación que no son los que se van a utilizar». Se sostiene
solo: entre los dos bloques hay **dos migraciones de esquema** (IDE.2 renombra `hub_sso_users`, IDE.5 cambia
`hub_module_grants`), **dos cambios de autorización** (IDE.1 la autoridad del rol, PLAT.5 los `require_module`) y
**el cambio de todas las URL del panel** (PLAT.2). Las tres clases de cambio son baratas antes de que haya personas
reales dentro y caras después: una migración sobre una base vacía no tiene riesgo, y cambiar la autorización cuando
nadie depende de ella no echa a nadie fuera.

**Con una salvedad de orden, que es una dependencia y no una preferencia**: PLAT.1 y PLAT.2 se ejecutan **antes** de
IDE, porque las pantallas de IDE.4 e IDE.5 cuelgan de `/plataforma` —la sección que crea PLAT.2— y porque mover
«Modelos LLM» a una sección en la que un admin no puede entrar le quita un acceso que hoy tiene, que es lo que
reparte PLAT.1. Los dos ya estaban marcados como adelantables por otro motivo: arreglan solos el 403.

**Y deja una tarea para el bloque Deploy**: IDE.1 introduce un ajuste nuevo —la autoridad del rol— que el inventario
de variables de entorno del despliegue tiene que incluir. Omitirlo significa desplegar con el valor por defecto sin
que nadie lo haya decidido.

**Coste asumido**: 12 prompts entre el cursor y D.0, y el piloto se retrasa lo que tarden. Es decisión del usuario.

**Deploy va ANTES de NIC**, y no por preferencia: `CLAUDE.md` §128 dice que `_legacy_nicegui/` se
borra «una vez verificado que todo lo migrado funciona en producción», y NIC.5 **es** ese borrado. Se
añaden tres razones: NIC.1 decide qué cuenta como «cubierto» y producción es el único sitio donde esa
respuesta se comprueba; NIC **no le ahorra nada al despliegue** (comprobado: el `Dockerfile` sólo
copia `shared/`, `server/app/`, `server/migrations/` y el `.venv` — `client_app/` nunca entra en la
imagen); y NIC.4 toca el `pyproject.toml` de la raíz, que es lo último que conviene mover justo antes
de desplegar por primera vez. Ese argumento sigue intacto: lo que cambió el 2026-08-22 es lo que va **antes** de
Deploy, no lo que va después. Secuencia vigente:
**PLAT.1 → PLAT.2 → IDE.1…IDE.5 → PLAT.3…PLAT.7 → Deploy (D.0–D.6) → pruebas humanas y RAG.6b → REV → NIC → REPO.**

**Ya alineado antes de D.0**: el `Dockerfile` construía en Python 3.11 y la suite corre en 3.13.
Corregido y verificado construyendo la imagen (Python 3.13.15 dentro, `xmlsec` y `onelogin.saml2`
importan, `server.app.main` con 163 rutas), con tres guardarraíles para que no vuelva a derivar.
**Pendiente aparte**: `requires-python` sigue en `>=3.11` en los cinco pyproject; estrecharlo obliga
a re-resolver cinco locks y no debe viajar con el despliegue.

### El orden, y por qué

**PLAT.1 → PLAT.2 → IDE → PLAT.3…PLAT.7 → Deploy → pruebas humanas y RAG.6b → REV → NIC → NIC.5 (el usuario borra `_legacy_nicegui/`) → REPO.**

Dos decisiones distintas lo fijan. La primera es del usuario (2026-08-21): **REPO no se ejecuta hasta
que la migración esté hecha**, porque no tiene sentido montar el repositorio definitivo y acto seguido
meterle la retirada de 500 ficheros de legacy. La segunda sale de `CLAUDE.md` §128: `_legacy_nicegui/`
se borra «una vez verificado que todo lo migrado funciona en producción», así que **NIC.5 no puede
preceder al despliegue** — y NIC.5 es lo que cierra la Fase 1.

**REPO no depende técnicamente de NIC.** Si abrir el repositorio pasara a tener fecha, se desengancha:
la dependencia dura es sólo la de los objetos huérfanos, que va de borrar el repositorio viejo y no
tiene nada que ver con el código legacy.

### Lo que espera a una persona, no a un agente

1. **Las pruebas manuales del Bloque INF**: `pruebas_manuales/pruebas_manuales_bloqueINF.bat`, cinco
   pasos. Lo irreducible: si el texto que la IA escribió sobre las tablas reales dice algo cierto, si
   el DOCX se lee, y los permisos por módulo, que necesitan dos cuentas.
2. **REPO.1 y REPO.2**, cuando NIC esté cerrado. Los pasos están en `Plan_TDD_Fase1.md` §Bloque REPO,
   versionados a propósito: el guion detallado vivía en `_local/`, que es ignorada y de usar y tirar.

### Lo que se hizo el 2026-08-21 y conviene no repetir

- **La raíz pasó de 89 entradas a 15 ficheros y 16 directorios.** La documentación a `docs/`, los
  planes y el cursor a `planificacion/`, los 15 `.bat` a `pruebas_manuales/` (cada uno con
  `cd /d "%~dp0.."` para seguir ejecutándose desde la raíz), y los datos de trabajo a `_local/`,
  que está ignorada. Borrado el código muerto: `desarrollo/`, siete scripts de un solo uso, `MAP.md`,
  `utils/`, `styles/`, `tmp/`, `copia/`, `data_test/`, `.benchmarks/`.
- **`HISTORIAL.md` es nuevo y es donde va el historial.** Se separó de este fichero porque era el 85%
  de sus 626 KB y este se lee entero al arrancar cada sesión; ahora son 104 KB. **Al cerrar un prompt
  la fila nueva va arriba de la tabla de `planificacion/HISTORIAL.md`**, no aquí.
- **AGPL-3.0-or-later**, con titularidad de la UJI, procedencia INNOVAP (Derecho Público e
  Innovación) y autoría de Modesto Fabra. Gobernanza en genérico —un principal y el fork de cada
  organización que despliega, sin fork privilegiado— y **DCO obligatorio, también en el principal**,
  comprobado por `.github/workflows/dco.yml`. Todos los commits van firmados (`git commit -s`).
- **Pendiente que la AGPL impone a este despliegue**: el §13 exige que una aplicación web ofrezca a
  sus usuarios el fuente de **la versión desplegada**. Tiene que ser configuración (`SOURCE_URL`), no
  una URL fija al principal, y verse también en el **widget público embebido**. Sin implementar.
- **Las acciones de CI a su major actual** (checkout/setup-python/setup-node/upload-artifact v7,
  download-artifact v8, setup-uv v10.0.1 fijada porque no publica mayor flotante). Y arreglado un
  rojo de CI que llevaba desde INF.4: el mock de `redaccion-llm-draft-preview.a11y.test.tsx` no tenía
  `useDescribeSampleFile`. **`npm test` no incluye la suite de accesibilidad**: al cerrar un bloque
  que toque frontend hay que correr también
  `npx vitest run --config vitest.a11y.config.ts --no-file-parallelism`.

## 👉 (2026-08-20, al planificar el Bloque INF)

**Cursor actual: INF.3.** INF.1 e INF.2 completos el 2026-08-20, y con ellos **el flujo del
módulo llega al final**: verificado en navegador de punta a punta sobre el informe real del
usuario, desde dos bloques de IA fallidos hasta `preview = 200` y `export = 200`.
**Modelo sugerido para el próximo prompt: Sonnet** — INF.3 tiene alcance cerrado: el 409 ya
trae `pending_block_ids`, y lo que falta es contarlo donde se ve y poder volver de la vista
previa.

**Los dos caminos del módulo de informes no llegan al final hoy.** Las dos causas de fondo, con su
sitio en el código, están en la fila del bloque en la tabla de arriba y desarrolladas en
`Plan_TDD_Fase1.md` §Bloque INF. En una línea cada una: hay **dos disparadores de la generación y uno
se salta la subida de datos**, y **el servidor y la pantalla no usan la misma definición de
«pendiente»**, así que un bloque de IA que falla bloquea el informe sin ofrecer ninguna acción.
**INF.1–INF.3 son los tres que desbloquean el flujo**; el resto no se puede probar de punta a punta
sin ellos.

**Decisión ya tomada por el usuario (2026-08-20)**: el control de acceso al módulo se resuelve **por
módulos concedidos, no con un rol nuevo**. Es INF.7, y es independiente del resto: puede adelantarse
si la apertura del módulo a toda la organización corre prisa.

**Un hallazgo del análisis sin confirmar**, y el único que puede ser un falso positivo: el usuario vio
el estado de cada bloque dos veces. Puede ser solo el `<span className="sr-only">` de
`WorkspaceEditor.tsx:74-76` saliendo al copiar el texto. Se comprueba en navegador en INF.8, antes de
tocar nada.

**El Bloque LEG está completo (LEG.1–LEG.5)** y con él **desaparece el último rojo conocido de la
suite**: 2488 passed, 3 skipped, 0 fallos, sin el flake de `tests/test_prompts.py`. El servidor ya no
escribe en la base de datos al arrancar, que era la causa común de ese flake y de los arranques
fallidos en desarrollo. **Medido de nuevo el 2026-08-20 con el venv reconstruido: 2618 passed, 1
skipped, 0 failed** (11:36 con `-n auto`).

**Siguen pendientes las tres tandas de pruebas
humanas**, todas escritas y en la raíz del proyecto:

1. `pruebas_manuales_bloqueVER.bat` — ocho pruebas, cubre VER + PRO + la PRUEBA H rehecha en GUI.
2. `pruebas_manuales_bloqueSEG.bat` — una sola pregunta: ¿sirve la valoración que propone la IA?
3. `pruebas_manuales_bloqueRAS.bat` — ¿son ciertos los hallazgos?, ¿molestó el rastreo al servidor?,
   ¿qué páginas merecen entrar en el asistente?

**Dos cosas que sólo puede hacer la persona**: preguntar a quien gestiona el portal por el rastreo
—el User-Agent es `GovGenAI-Curacion/1.0 (+contacto)`— y por la línea del `robots.txt` que excluye a
ClaudeBot de `www.uji.es`.

**Y una decisión pendiente sobre el árbol de trabajo**: los dos ficheros de entrada del informe de
doctorado siguen en la raíz sin añadir a git (`Informe Resumen Programa de Doctorado en Ciencias
(90162).md` y `Prompt_informe.txt`). Conviene moverlos fuera o ignorarlos.

Debajo, el registro del cierre de RAS.

## 👉 (2026-08-18, al cerrar el Bloque RAS)

**El Bloque RAS está completo (RAS.1–RAS.5)** y el rastreo del apartado de la Escuela de Doctorado
funciona de punta a punta: 351 páginas en 12 minutos, rastreo completo, **20 hallazgos y los 20
ciertos** (venían 500). Detalle y coste en `docs/CASO_CURACION_ESCOLA_DOCTORAT.md`.

**Lo siguiente son las dos pruebas humanas pendientes**, que ya están escritas:
`pruebas_manuales_bloqueRAS.bat` (¿son ciertos los hallazgos? ¿el rastreo molestó al servidor? ¿qué
páginas merecen entrar en el asistente?) y `pruebas_manuales_bloqueSEG.bat` (¿sirve la valoración que
propone la IA?). Y sigue pendiente `pruebas_manuales_bloqueVER.bat`.

**Dos cosas que la persona tiene que hacer y el agente no puede**: preguntar a quien gestiona el
portal si el rastreo aparece en sus registros —el User-Agent es `GovGenAI-Curacion/1.0 (+contacto)`—
y decidir qué hacer con la línea del `robots.txt` que excluye a ClaudeBot de todo `www.uji.es`.

**Bloque LEG** sigue planificado y sin ejecutar (retirada del legacy de prompts, que es lo que
colisiona con la suite).

**Un límite conocido del rastreo**: cada página del portal repite su menú completo, y eso viaja al
corpus con el contenido. Quitar el *boilerplate* no está hecho.

Debajo, el registro del cierre de SEG.

## 👉 (2026-08-18, al cerrar el Bloque SEG)

**El Bloque SEG está completo (SEG.1–SEG.5)** y con él el módulo de Informes hace lo que el
usuario describió: las tablas se pintan del dato, la valoración la propone la IA sobre **su** tabla
y el técnico la aprueba o la edita. Verificado con el informe real de un programa de doctorado.

**Lo siguiente es la persona, y es una sola pregunta**: `pruebas_manuales_bloqueSEG.bat` —¿la
valoración que propone la IA le sirve a quien firma el informe? Todo lo mecánico está comprobado en
navegador y no se repite.

**Sigue pendiente el `.bat` anterior**: `pruebas_manuales_bloqueVER.bat` (ocho pruebas, cubre VER +
PRO + la PRUEBA H rehecha en GUI).

**Dos bloques planificados y no ejecutados**: **LEG** (retirada del legacy de prompts, que es lo que
colisiona con la suite) y **RAS** (rastreo de un portal real, con la Escuela de Doctorado como caso
guía — la misma unidad que el caso de SEG).

**Un aviso sobre el árbol de trabajo**: en la raíz del repo hay dos ficheros sin seguimiento que
son datos de entrada del usuario (`Informe Resumen Programa de Doctorado en Ciencias (90162).md` y
`Prompt_informe.txt`). **No se han añadido a git a propósito** —informes fuente fuera del repo— y
conviene decidir si se mueven fuera o se ignoran, para que un `git add -A` no los suba.

Debajo, el registro del cierre de GUI.

## 👉 (2026-08-18, al cerrar el Bloque GUI)

**El Bloque GUI está completo (GUI.1–GUI.6)** y salió de una sola frase del usuario al ir a
probar: las plantillas no se podían borrar ni editar. Detrás había cinco huecos del mismo tipo, y
el peor era que **la PRUEBA H no se podía hacer**: el borrador no podía proponer un bloque de
transformación, así que el ETL de PRO.4 y PRO.9 era inalcanzable desde la interfaz. Ya se puede,
y está verificado con el modelo real sobre una hoja con importes en texto.

**Lo siguiente sigue siendo la persona**: `pruebas_manuales_bloqueVER.bat` (ocho pruebas, cubre
VER + PRO) **con la guía de pantallas** que se entregó como artefacto. La PRUEBA H está rehecha
para el camino que ahora existe.

**Un hueco conocido y no cerrado**: no hay pantalla para editar los bloques de un informe ni para
aplicar lo que el copiloto propone. Los bloques se crean describiendo el informe. Documentado en
la guía y en el propio panel.

Debajo, el registro del cierre de PRO.

## 👉 (2026-08-17, al cerrar PRO.8 y PRO.9)

**PRO.8 y PRO.9 están cerrados, y ahora sí toca la persona.** Los dos salieron del mismo criterio
del usuario —lo usual se elige sin programarlo— y en los dos la comprobación dio algo que no se
esperaba: en gráficos, que pedir «barras horizontales» costaba **generar un script** y que una
plantilla **no podía ni poner un título**; en ETL, que **lo determinista del legacy ya estaba
portado entero**, así que lo que faltaban eran cuatro operaciones que allí tampoco existían.

**Lo siguiente: `pruebas_manuales_bloqueVER.bat`** en la raíz (cubre VER **y** PRO). **Ocho
pruebas**, y las tres que importan de PRO son **F** (calidad del script sobre un fichero real de
la UJI), **G** (si el copiloto es útil o sólo correcto) y **H, nueva** (una hoja de cálculo tuya
de verdad: que el plan ponga `to_number` antes de sumar, y que una hoja en formato inglés falle
diciéndolo en vez de dar otra cifra).

Debajo, el registro de cierre de los siete primeros prompts.

**El Bloque PRO está completo**, con PRO.2.1 añadido a mitad de camino. El módulo de Informes
ya hace de punta a punta lo que prometía: pedir un script en lenguaje natural, auditarlo con dos
modelos de dos niveles, ejecutarlo en el sandbox contra un fichero real, aprobarlo, extraer con
él dentro de un informe, transformar los datos, dibujar un gráfico, **ver todo eso en la vista
previa** y **descargar el DOCX**. Y el copiloto responde con citas a la documentación real.

**Lo siguiente, y ahora sí depende de una persona: `pruebas_manuales_bloqueVER.bat`** en la raíz
(cubre ya VER **y** PRO). Siete pruebas —ocho al cerrar PRO.9—, y dos son las que importan de la
primera mitad de este bloque:
**F — la calidad del script del modelo sobre un fichero real de la UJI** (el agente prueba con
un Excel sintético cuyas columnas inventó él, así que no puede saber si la tabla es la que se
pedía) y **G — si la respuesta del copiloto es útil o sólo correcta**. Las otras cinco siguen
siendo las de VER: calidad editorial, exportación abierta en Word y Adobe, anonimización con
datos reales, rastreo de una web con enlaces en HTML y el asistente de Gerencia contra su
gemelo agéntico.

Después, el **despliegue del prototipo en GCP** (`docs/DESPLIEGUE_PROTOTIPO_GCP.md`), que sigue
pendiente de dos cosas del usuario: las cuentas locales para los probadores de Gerencia y la
credencial del sitio publicado en el bucket.

**Dos cosas anotadas y no hechas, cada una candidata a prompt propio**: (1) retirar el legacy de
prompts **de este repositorio** —`ExtractionServiceConfig`, `seeds_prompts.py` y el `main.py` de
la raíz, con `tests/test_prompts.py` sembrando la base de datos del desarrollador y siendo
inestable con `-n auto`—. ~~(2) los diez tipos de gráfico del legacy~~ **→ pasó a ser PRO.8**.

**Una cosa del entorno que quedó así, a propósito**: el sandbox del stack de producción no
publica su puerto, así que para probarlo desde un backend en el host se levantó una instancia
aparte en el 5099.

> ⚠️ **Corregido el 2026-08-20: el «huérfano del 8000» no era inmatable.** Esta nota decía que
> el backend de desarrollo corría en el **8001** porque el 8000 lo retenía «un proceso huérfano
> que no responde a `taskkill`», y de ahí la deriva a 8001 y luego al 8002 de
> `frontend/.env.local`. **Ninguna de las dos mudanzas hacía falta.**
>
> El mecanismo real: cuando uvicorn `--reload` falla en el arranque (típicamente por la BD
> apagada), **el árbol de procesos no muere**. El padre se queda con el socket en estado
> **`Bound`**, no `Listening`, así que `netstat | findstr LISTENING` no lo ve —el puerto parece
> libre— pero `bind()` falla con `WinError 10048`. Lo que no funcionaba era matar **un** PID:
> el resto del árbol mantiene el socket. Matando los tres a la vez el puerto se libera.
>
> ```powershell
> Get-NetTCPConnection -LocalPort 8000 | Select LocalAddress,State,OwningProcess
> Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select ParentProcessId,CommandLine
> Stop-Process -Id <los PID del árbol entero> -Force
> ```
>
> `frontend/.env.local` vuelve a apuntar al **8000**, que es lo que levanta `arranque.bat`.
> Mientras apuntaba al 8002 y el backend arrancaba en el 8000, toda llamada a la API desde el
> frontend en dev daba 502. Si el 8000 vuelve a dar 10048, se limpia el árbol; no se cambia de
> puerto.

**Fuera del alcance de VER, documentado**: `POST /redaccion/scripts/propose` y
`POST /redaccion/copilot/ask` siguen siendo stubs 503 por decisión del usuario.

El Bloque PIL quedó completo el 2026-08-15; el registro anterior se conserva debajo.

---

**Lo siguiente era el Bloque PIL**, que es lo que convierte la plataforma en algo que se puede
enseñar: los dos asistentes del piloto con el corpus normativo real (298 y 124 documentos),
embeddings por Vertex y pruebas en local antes de desplegar. Empieza por **PIL.1** (el
adaptador de Vertex y el embebido por lotes), que bloquea toda la ingesta. Prerrequisitos que
aporta el usuario: Docker arrancado, y proyecto/región de GCP con la Vertex AI API habilitada
y credenciales ADC en la máquina.

D.0 (Deploy) sigue esperando los mismos datos de GCP, y MAN.2 sigue esperando ejecución
humana. El registro anterior se conserva debajo.

**Cerrados desde la última revisión del cursor**: SEC.8 (los 8 prompts), EXT (los 3) y FAQ
(los 2). Suite backend **1819 passed, 3 skipped, 0 failed**; frontend 281; `tsc` limpio.

**El usuario está extrayendo los XML consolidados del BOE**, que es el prerrequisito de la
base documental de Gerencia. Mientras tanto, lo que se puede avanzar en la aplicación **sin
depender del corpus**, por orden de valor:

1. ~~**D.4.0**~~ ✅ **hecho el 2026-08-11** (`c92dc47`). La app pasa de 627 MB a **345 MB** y
   arranca en **9,4 s** sin el extra. `e2-small` basta para la VM.
2. ~~**Arreglo de los perfiles de grafo sin configurar**~~ ✅ **hecho el 2026-08-11**
   (hallazgo I5). Eran **dos**, no uno, y el test de contrato certificaba que compilaban.
3. ~~**REV.1**~~ ✅ **hecho el 2026-08-11**. El veredicto del revisor, con su cola de
   pendientes, sus filtros y sus columnas en el CSV. Migración `v9e0f1g2h3i4` aplicada.

4. ~~**FIX.4**~~ ✅ **hecho el 2026-08-11**. La carga del corpus embebe con el modelo
   configurado, comprueba el espacio vectorial **antes de escribir**, y **vuelve a
   arrancar**: estaba rota con SIGSEGV en Windows desde D.4.0.

5. ~~**DER.1**~~ ✅ **hecho el 2026-08-11**. `--chatbot-id` repetible: el mismo corpus en
   varios asistentes en una pasada, leído y validado una sola vez.

6. ~~**DER.2**~~ ✅ **hecho el 2026-08-11**. Hallazgo `copia_divergent`, aviso antes de borrar
   con borrado en cascada opcional, y aviso de deriva al terminar cada carga.

7. ~~**DER.3a**~~ ✅ **hecho el 2026-08-11**. `docs/REQUISITOS_PUBLICACION_PLATAFORMA.md`,
   para llevar a la reunión con la unidad de desarrollo.

**El bloque DER queda cerrado en todo lo que no depende de terceros.** DER.3 sigue bloqueado
a la espera de que la unidad de desarrollo conteste al entregable. La carga del corpus está
lista para los dos asistentes del piloto.

**Lo siguiente, si no hay otra prioridad**: el Deploy GCP (D.0), que espera datos tuyos
—proyecto, región, credenciales—, y MAN.2, que espera ejecución humana.

**El bloque COR quedó planificado y descartado el mismo día (2026-08-11)**: compartir el
documento entre chatbots no compensa. La deduplicación de fragmentos solo se dispararía si
coincidieran modelo de embedding y estrategia de troceado, y el piloto **varía la estrategia
a propósito**; el problema de mantenimiento se resuelve con un solo `.md` en disco y dos
cargas incrementales; y las filas separadas conservan que cada asistente elija su modelo de
embedding. Razonamiento completo —incluidos **dos argumentos míos que eran incorrectos**— en
la cabecera del bloque en `Plan_TDD_Fase1.md`. Queda un candidato sin planificar: un hallazgo
de curación que detecte **deriva** entre copias de la misma norma.

**Pendiente de acción del usuario, no de código**: MAN.2 (ejecutar
`pruebas_manuales_plataforma.bat` de principio a fin; el paso de subir un PDF al corpus ya se
actualizó a `.md` tras EXT.1). Y **D.0/D.2/D.3** esperan datos de GCP (proyecto, región,
credenciales), no al corpus.

**Modelo sugerido: Sonnet** para D.4.0 y REV.1.

---

**Cursor: Bloque PIL (PIL.1), y detrás el Deploy GCP empezando por D.0. MAN.2 espera ejecución humana** — **BLOQUE CAL COMPLETO el 2026-08-09** (CAL.1 `944bb48`, CAL.2 `bec3300`, CAL.3 `393ce03`, CAL.4 `57d538a`, CAL.5 `d13353f`, cierre `5c7774d`, CAL.4.1 `7e4f435`) y **BLOQUE CUR COMPLETO el 2026-08-09** (CUR.1 `d1b9453` + fix `fd39ee9` + fix `d9ed15f`, CUR.2 `ca53cd5`). **BLOQUE SEC COMPLETO**: SEC.1 (`3a7b5a4`), SEC.2 (`2ad9125`), SEC.2.1 (`3c4fa24`), SEC.3 (`35cfdcb`), SEC.4 (`7127e36`), SEC.4.1 (`2ddc121`), SEC.5 (`d59c842`), SEC.7 (`d0712b6`), FIX.2 (`18f8969`) y FIX.3 (`1f58f53`).

> 🧹 **Tres scripts huérfanos borrados (Caso B, decisión del usuario el 2026-08-03).**
> `scripts/verify_fix.py`, `scripts/diagnose_startup.py` y `scripts/init_rpa_prompts.py` eran
> los únicos llamantes del shim `init_db` que retiró CAL.5. Importaban rutas anteriores al
> monorepo (`app.database.*`, `app.services.*`, `app.core.*`) que ya no existen, así que **no
> podían ejecutarse**; ni siquiera entre ellos —`diagnose_startup` llamaba a un
> `init_rpa_prompts` de `app.database.seeds` que `main.py:91` ya documentaba como inexistente—.
> Nadie los invocaba desde fuera. El historial de git es la fuente de verdad de lo que hacían.

> ⚠️ **La suite backend en paralelo también da un falso rojo en esta máquina.**
> `tests/infra/test_setup_script.py::test_should_check_docker_and_required_ports` invoca
> `bash setup.sh --dry-run` con un timeout de 60 s; con `-n auto` y 16 workers compitiendo, el
> script no acaba a tiempo y el test cae por **TimeoutExpired, no por aserción**. En serie el
> fichero da **12 passed en 10 s**. Es el gemelo backend de la nota de vitest de más arriba: si
> ves ese rojo, reprodúcelo con `-n0` antes de investigarlo. (CLAUDE.md ya avisa de este
> fichero por un motivo emparentado —resolución de `bash`—, pero la causa aquí es la
> contención, no PowerShell: la sesión corría desde Git Bash.)

> ⚠️ **Por qué existe CAL.4.1 (deuda medida que dejó CAL.4).**
> La paridad que CAL.4 dejó verde es de claves **del diccionario**, y la pantalla de documentos
> casi no tiene: **41 claves viven sólo como *default* dentro del `t('clave', 'texto')` del
> código** y no existen en `es/ca/en admin.json`. El efecto se ve a simple vista poniendo
> `i18nextLng=ca` en `localStorage`: la navegación sale en catalán y **el cuerpo de la pantalla
> se queda en castellano**, que es justo lo que CAL.4 pretendía arreglar. Reparto medido:
> `DocumentsTable` 12, `IngestionJobsPanel` 7, `RechunkControls` 7, `DocumentsPage` 5,
> `RetrievalBanner` 4, `UploadDropzone` 4, `DocumentBadges` 2.
>
> **El test de paridad no lo caza por construcción**: lo que no está en el diccionario no se
> compara con nada. Por eso CAL.4.1 tiene que añadir un guardarraíl distinto —que ninguna clave
> del namespace `admin` viva sólo como default— y no basta con ampliar el de paridad.
>
> No se absorbió en CAL.4 porque el prompt acotaba `DocumentsPage` a *sus constantes*, y
> ampliarlo sobre la marcha habría vuelto a inflar un prompt que ya se había desbordado en
> CAL.2. Queda como prompt propio, que es lo que era.
**El uvicorn zombi ya no bloquea las pruebas manuales**: el PID 7576 del 2026-08-02 (arrancado sin `--reload`, quedándose `127.0.0.1:8000` por delante del reiniciado en `0.0.0.0:8000`) se paró el 2026-08-03 al verificar CAL.2 en navegador. Si vuelve a aparecer un 8000 duplicado, la comprobación es `Get-NetTCPConnection -State Listen -LocalPort 8000`. Lo único que no se puede probar en local sigue siendo el **SSO SAML real contra el IdP**.

> ⚠️ **La suite de vitest en paralelo da falsos rojos en esta máquina.** Con `-n auto` (el
> defecto) caen entre 1 y 15 tests por pasada, siempre distintos y casi todos con
> `STACK_TRACE_ERROR` —que es como vitest marca un *timeout*—, más el clásico «Axe is already
> running» de `A11y.test.tsx`. Los mismos ficheros pasan sueltos y **la suite entera da
> 255/255 con `--no-file-parallelism`**. Antes de investigar un rojo de vitest, reprodúcelo en
> serie; si en serie pasa, es contención, no regresión. Es el mismo motivo por el que CI del
> backend corre con `-n0` (ver TST.1).

---

## ✅ CAL.2 cerrado — la capa API del frontend sale del contrato (2026-08-03)

*(El traspaso «CAL.2 analizado y sin empezar» que ocupaba este sitio queda resuelto: ejecutado
entero, verificado en navegador y commiteado. Lo que sigue es lo que hay que saber para CAL.3.)*

### Lo que resultó ser el trabajo de verdad: el contrato no tenía los tipos

El prompt pedía «usar los tipos de `generated/model` (IngestionJob, HubDocument…)». **Esos tipos
no existían**, y no por un despiste de Orval: **los endpoints no declaraban `response_model`**, así
que FastAPI los documentaba como objeto vacío y Orval los generaba como `Promise<unknown>`. Migrar
a los hooks sin arreglar eso habría *movido* la interfaz escrita a mano de `shared/api/*.ts` a la
página, no eliminado. Por eso CAL.2 empieza en el backend:

- **`hub_ingestion_router.py`** — 10 modelos nuevos: `IngestionJob`, `IngestionJobsOut`,
  `HubDocumentOut`, `HubDocumentDetailOut`, `HubDocumentsOut`, `UploadDocumentOut`,
  `DeleteIngestionJobOut`, `ClearCollectionOut`, `AnalyzeHtmlOut`, `MessageOut`. Los 8 endpoints
  del panel declaran ya `response_model`.
- **`hub_feedback.py`** — `InteractionReviewOut` sustituye a `list[dict]`.
- **`hub_llm_configs_router.py`** — `AvailableModelsOut` y `LLMConnectionTestOut`, los dos huecos
  que quedaban en un router que ya tenía tipado el resto.

**Decisión que no se rediscute: `IngestionJob.status` es `str`, no `Literal`.** Es un campo de
presentación, la tabla ya tiene rama por defecto, y un valor inesperado en una fila debe pintarse
«en cola», no tumbar el listado entero con un 500 de validación de respuesta.

### La trampa de los `response_model` sobre objetos ORM (costó 3 rojos)

`chunks_processed`, `progress_current`, `progress_message`, `processing_stats` y `created_at` son
**NOT NULL con `default=` de SQLAlchemy**, o sea que el valor lo pone el *flush*, no el constructor.
Una fila leída de la BD siempre los trae; un `HubIngestionJob(...)` recién construido los tiene a
`None`. Tres tests montaban la sesión con `AsyncMock`, así que su job nunca pasaba por el flush y
el `response_model` nuevo lo rechazaba con razón. **Arreglado en los dobles, no en el modelo**:
`test_ingestion_storage.py` tiene ahora un `refresh` que rellena los defaults como haría el real, y
`test_job_progress.py` construye el job completo. Si añades un `response_model` sobre un objeto ORM,
mira primero qué columnas dependen del flush.

**Y no recortes campos al tipar**: la primera versión de `IngestionJob` se dejó fuera
`processing_stats`, que el endpoint sí devolvía —el `response_model` filtra en silencio— y tumbó el
test de progreso de RAG.12. El modelo describe lo que ya se sirve; no es la ocasión de podar.

### Retirada del panel de fuentes: hecha

Se ejecutó la opción B ya decidida. `DocumentsPage` pasa de **1.019 a ~610 líneas** y de 3 pestañas
a ninguna (con una sola vista, la barra sobra). Fuera: `AdminIngestionAssistant.tsx` y su test, y
los 5 módulos manuales de `shared/api/`. El analizador de HTML (`/hub/ingestion/analyze-html`,
endpoint vivo) cae con el asistente porque su botón de guardar iba al 404 de `createSource`;
recuperarlo es repuntarlo a `/hub/sites/{id}/analyze`, y eso es producto, no limpieza.

### Dos extensiones sobre el alcance literal del prompt

1. **`copilotApi.ts` también se retira.** El prompt nombra 5 módulos, pero su criterio de cierre
   (`grep localhost:8000` = 0) lo alcanza, y su propio `// TODO CF.4` decía «cuando openapi.json se
   regenere con `/redaccion/copilot/*`» — ya está regenerado. Único consumidor: `CopilotPanel`.
2. **`LoginPage` deja de construir su `API_BASE`.** Ahora importa `apiBaseUrl` de `client.ts`, que
   es el único sitio del frontend donde vive el host. Su `fetch` **se queda**: el bucle de dos rutas
   con manejo explícito del 401 (SEC.1) no se traduce a axios sin cambiar comportamiento, y ahí no
   hay cabecera de autenticación que centralizar.

### `client.ts` ahora traduce `detail` a `error.message`

Al pasar de `fetch` a axios, las pantallas que pintan `err.message` habrían empezado a mostrar
«Request failed with status code 409» en vez del motivo. El interceptor de respuesta copia el
`detail` de FastAPI (string o lista de errores de Pydantic) a `message`. **Sin esto, migrar a Orval
degrada todos los mensajes de error del panel** — y no lo habría cazado ningún test de tipos.

### El guardarraíl que impide la recaída

`frontend/src/shared/api/__tests__/contractFirstApi.test.ts` lee el árbol de fuentes y falla si
alguien reintroduce un módulo API a mano, un `fetch` en `DocumentsPage`, un `localhost:8000` fuera
de configuración, o una cabecera `Authorization` construida fuera de `client.ts`. **Único exento:
`widget/hooks/useChat.ts`** (SSE; Orval no lo cubre y axios no expone el cuerpo incremental).
Exigió añadir `"node"` a `types` en `tsconfig.app.json`.

### ⚠️ Tras `git pull` de este commit hay que regenerar el contrato

`server/openapi.json`, `frontend/openapi.json` y `frontend/src/shared/api/generated/` están en
`.gitignore` (líneas 103-107), así que **el commit no los lleva**. Como CAL.2 introduce tipos
nuevos que el frontend importa, sin regenerar **el `tsc` falla**:

```
cd server;   uv run python export_openapi.py
cd frontend; npm run generate:api
```

### Desviaciones documentadas

- **Nombres**: el prompt sugería `HubDocument`; se usa **`HubDocumentOut`** porque `HubDocument` ya
  es la clase ORM en `operational_models.py` y colisionaría en el router. `IngestionJob` sí es literal.
- **Dos rojos preexistentes de `tsc` arreglados** para poder cumplir el criterio de cierre
  («tsc --noEmit en verde»), ambos ajenos a CAL.2: una prop `expandido` muerta en
  `TestScenariosPage` (el `<details>` gestiona su propio estado) y un cast que necesitaba
  `as unknown as` en `rol2_rename.test.tsx`.
- **Los tests que stubbeaban `fetch` global ahora doblan los hooks generados** (Organizaciones,
  AIBrain, LLMConfigs, Prompts, CopilotPanel). No es cosmético: axios **no pasa por `fetch`**, así
  que esos stubs habían dejado de interceptar y los tests medían pantallas vacías.

---

## ✅ SEC.2 y SEC.2.1 cerrados — el modelo de autorización, en una página

*(El traspaso «SEC.2 a medias» que ocupaba este sitio queda resuelto: los 6 rojos arreglados, el gate probando endpoints y todo commiteado. Detalle en las filas de SEC.2 y SEC.2.1 del historial.)*

### El modelo de tenencia, en cuatro líneas

- `UserInfo.organizacion_ids` + claim `orgs` en el JWT. Un token anterior a SEC.2 se lee **sin acceso**, no con acceso total.
- `server/app/core/auth/tenancy.py`: `puede_acceder`, `assert_org_access`, `scope_query_to_orgs`, `orgs_del_principal`. **Vacío significa lo contrario según el rol**: en un superadmin es «todas», en cualquier otro «ninguna».
- Frontera aplicada en `hub_chatbots_router` (listado acotado en SQL + `_get_chatbot_or_404` como único punto de lectura), `hub_chat`, `hub_feedback`, `hub_themes_router` y `hub_ingestion_router`.
- Claim poblado en el login de admin (organizaciones por `partner_id`) y en PAT (**heredado del dueño y resuelto en cada validación**: guardarlo en la fila lo congelaría y una revocación dejaría de revocar).

### Lo que añadió SEC.2.1

- **`assert_chatbot_access`** (`core/auth/chatbot_access.py`) es el único sitio donde se decide si alguien puede conversar con un chatbot: organización **y** modo de acceso, juntos. `hub_chat` ya no llama a `assert_org_access` por su cuenta, y hay un test que falla si el adaptador OpenAI (OWUI.1) o el endpoint del widget (D.1) nacen sin pasar por él.
- **`EffectiveActor` + `resolve_effective_actor`** (`core/auth/delegated_actor.py`): quién pregunta de verdad cuando la petición llega por un cliente de confianza. Lo consumirá la cuota de SEC.4 — se escribe **sobre el actor**, no sobre el principal, o la contabilidad por usuario nace mal.
- **`SAML_ORGANIZACION_ID`**: la organización del IdP. Un usuario SSO ya no entra sin acceso a nada.

### Lo que queda apuntado para más adelante

1. **La cabecera delegada no tiene consumidor todavía.** Está probada a nivel unitario; quien la usa de verdad es el Pipe de OWUI (OWUI.3), y el `via='widget_api_key'` de `assert_chatbot_access` espera a D.1. Ninguno de los dos bloquea nada ahora.
2. **RS256 para la cabecera** cuando haya más de un cliente delegante: cada uno querrá su clave y su rotación. Hoy hay uno, y HS256 con secreto compartido es lo proporcionado.
3. **El SSO real contra el IdP sigue en pruebas manuales pendientes** — la organización del IdP se ha probado contra la BD, no contra el IdP institucional.

### Tres decisiones que no se rediscuten

1. **`organizacion_ids` y `saml_groups` son tuplas, no listas** (el plan decía lista en los dos casos). `UserInfo` es `frozen` para que nadie amplíe permisos a mitad de petición, y una lista dejaba `.append(...)` disponible. Vale igual para los grupos, que ahora deciden el acceso en modo `restricted`.
2. **Un tema sin `organizacion_id` es de plataforma y exige superadmin**, y la organización del cuerpo se **valida** contra el token en vez de derivarse de él. Verificado que ninguna pantalla del frontend consume `/api/v1/hub/themes`, así que nadie empieza a recibir 403 por esto.
3. **`restricted` con las listas vacías no deja pasar a nadie salvo al superadmin.** La lectura contraria —«no hay restricción declarada, luego no restrinjo»— convierte un descuido de configuración en un chatbot abierto. Igual con un `access_mode` que el código no reconozca: no se interpreta, se cierra.

---

**Nota del cierre de SYNC (ya resuelta por SEC.1)**: se detectó que `/api/v1/auth/admin/login` no verificaba la contraseña. Cerrado en `3a7b5a4`.
**DEUDA DEL BLOQUE RAG: CERRADA el 2026-08-02.** La baseline del gate está regenerada en **MRR 0,940 · recall@5 0,960 · recall@10 0,960** (antes 0,8613 de RAG.1), así que la mejora de RAG.7 ya está protegida. Y los 0,02 están cuadrados **por medición, no por hipótesis**: son **una sola consulta** —«qui tutoritza les pràctiques externes?»— que pasa de rango 2 a rango 1, lo que vale exactamente 0,5/25 = 0,02. **La hipótesis de HNSW queda refutada**: con 52 chunks el planificador nunca toca el índice vectorial (`EXPLAIN` da `Sort` + top-N heapsort sobre un Index Scan por `chatbot_id`). Lo que hay debajo es un **empate exacto de coseno** (0,316227773316) entre dos fragmentos de documentos distintos, y el `ORDER BY` de las dos ramas del retriever **no tiene desempate**: cuál de los dos queda primero lo decide el plan de la consulta, no la recuperación. Detalle y controles en el historial.
**Recordatorio del orden vigente**: tras RAG.7→RAG.14 van SYNC, resto de SEC y CAL; después **Deploy empezando por D.0** (habilita los nueve servicios de GCP de una vez) y, solo entonces, **RAG.6b** (adaptador de Vertex + medición del valenciano), que depende de que D.0 haya habilitado Discovery Engine.

> **Por qué TST fue delante de RAG.2 (cerrado el 2026-07-30).** Quedan 39 prompts y todos se cierran comparando la suite. Esa comparación arrastraba 10 fallos que aparecían y desaparecían según la selección de tests, así que «sin regresiones» era una afirmación con asterisco. Ya no: `unit`+`integration` juntos dan 0 fallos y los guardarraíles de `tests/infra/test_suite_hygiene.py` impiden la recaída. **TST.3 (2026-07-30) cerró la deuda residual**: cero fallos y cero errores en toda la suite. **Ya no hay nada que filtrar al comparar la suite** — si aparece un rojo, es real.

> **La carga del corpus v1 queda pendiente y ya no bloquea nada.** RAG.1 resultó no necesitarla: construye su propio corpus de fixture (25 normas breves, embedding determinista) para el gate de CI. La carga real conviene hacerla cuando el front-matter esté completo — ya existe el script que lo emite y `md_frontmatter/` tiene los 226 con `url_oficial`, `title`, `language` e `id_publicacio`; faltan la revisión de consolidación en el panel y las columnas de catálogo del Hito A. Cuando toque: `bootstrap` → `ingestion.corpus.load --census --dry-run`.
>
> **Herramientas del corpus entregadas fuera del repo** (en `Descarregar_pdf/normativa_propia/publicacio_transparencia_2026-07/`): `genera_frontmatter.py` (front-matter derivado del catálogo + bloque `consolidacio` + clases de estado en los encabezados), `build_dashboard_consolidacio.py` (panel de revisión → `decisions_consolidacio.json`) y el parche de `build_pagines.py` para que el HTML emita `id` por artículo, que es lo que permite el enlace profundo desde el panel. El chunker del hub soporta `{#ancora .classe}` desde el fix del 2026-07-29.

> ✅ **BD de desarrollo reparada (2026-07-28).** Estaba sellada en `y6h7i8j9k0l1` con **cero tablas `hub_*`**: el esquema de `agents_hub` se perdió al recrear la BD durante el renombrado `AI_agents_hub`→`govgenai`. Reparada con la opción aprobada por el usuario: `create_all` desde el metadata del ORM **sin tocar las 56 tablas existentes ni mover `alembic_version` a mano**, dejando fuera `hub_vocabulary_terms` para que la creara su propia migración y el sello avanzara por la vía normal. Estado final: **79 tablas (23 `hub_*`), `alembic_version = z7i8j9k0l1m2`**. Después se alinearon **81 `server_default`** que `create_all` no pone (el ORM los declara del lado Python) tomando la referencia de una BD construida con `alembic upgrade head`: **0 diferencias** en las columnas comunes de las 23 tablas. La BD sigue **sin sembrar** (`bootstrap.py` pendiente, lo ejecuta el usuario porque fija la contraseña del SuperAdmin); ING.0.2 no lo necesita, ING.0.5 sí.
>
> 🐞 **Hallazgo de la comparación — fallo de despliegue en instalación limpia.** El ORM declara `HubIngestionJob.canonical_url` y `.original_filename` (`operational_models.py:237-238`) pero **ninguna migración las crea**: `e5f6a7b8c9d0` las trata como opcionales (`if _column_exists(...)`) porque las creó código fuera de la cadena. En una instalación limpia no existen, y `POST /hub/ingestion/upload` las escribe (`hub_ingestion_router.py:228`, más `watcher.py:266,277`) ⇒ **la subida de documentos revienta en un despliegue nuevo**. Es la misma familia que el fallo de `hub_ingestion_sources` que arregló 11.2. Se corrige en **ING.0.2**, que ya es el prompt de migración del modelo de datos de ingesta. Tercera diferencia, inocua: `hub_interactions.metadata` existe en instalación limpia y el ORM no la declara (columna muerta). **Fase 11 completa (11.1→11.3)** y **SEC.6 completo** (adelantado). Siguiente en el orden: ING.0 (ING.0.1→ING.0.5) → carga del corpus v1 + pruebas manuales → RAG.1 (baseline) → RAG.2 (consolidación) → **Bloque VIS (VIS.1→VIS.3)** → resto del Bloque RAG (RAG.3→RAG.14) → **Bloque SYNC (SYNC.1→SYNC.2)** → resto de SEC → CAL → Deploy GCP.

> **ORDEN VIGENTE (reescrito el 2026-08-03; manda sobre cualquier lista anterior de este fichero).**
> Hecho desde la última revisión: **RAG completo** (RAG.6a→RAG.14) · **Bloque DET ✅** ·
> **Bloque SYNC ✅** · **Bloque SEC ✅** (+FIX.1/FIX.2/FIX.3) · **Bloque CAL ✅** (CAL.1→CAL.5).
>
> **Quedan 17 prompts para cerrar la Fase 1**, en este orden:
> 1. **CAL.4.1** (1) — las 41 claves de la pantalla de documentos. **Decisión del usuario: la próxima sesión empieza aquí.**
> 2. **Bloque CUR** (2) — CUR.1→CUR.2. Va **antes** del Deploy y no después: los artefactos de D.4/D.5 codifican la estructura de módulos y la clasificación de routers, así que decidirla luego obliga a rehacer el pipeline y a repetir la verificación en producción. Un refactor pre-deploy sólo arriesga en local.
> 3. **Bloque MAN, parte local** (3) — MAN.1→MAN.3. Van **después de CUR** a propósito: CUR mueve módulos, y escribir los guiones antes sería documentar una estructura que está a punto de cambiar. Y van **antes del Deploy** porque un fallo encontrado en local cuesta un prompt; encontrado en producción cuesta un despliegue.
> 4. **Deploy GCP** (6) — D.0 primero, que habilita los nueve servicios de una vez —decisión del usuario del 2026-08-01— y sin el cual D.1-D.5 asumen APIs encendidas que nadie encendió.
> 5. **MAN.4** (1) — campaña contra el entorno desplegado. SSO SAML real, sistemas externos, Cloud Run/Cloud SQL/GCS y edge vs cloud. **No se puede empezar antes de D.5.**
> 6. **RAG.6b** (1) — adaptador de Vertex y medición del valenciano. **Después de D.0 y no antes**: el Ranking API vive en Discovery Engine.
> 7. **Bloque OWUI** (3) — OWUI.1→OWUI.3, post-deploy.
>
> **La carga del corpus v1 no bloquea a ninguno de estos** y no es un prompt, pero sí desbloquea dos mediciones que están anotadas y sin hacer: BGE-M3 contra Google a 1024 en valenciano (que **no** necesita el deploy, porque los embeddings van por API key de Gemini) y la traza del asistente con corpus real.
>
> **Las pruebas manuales del Bloque SEC quedan absorbidas por MAN.2**: reejecutarlas sueltas ahora sería la tercera pasada sobre un guion que CAL.2/CAL.3/CAL.4 han dejado a medio caducar.

> **Nota para ING.0.5**: la validación de subidas ya existe y es reutilizable — `server/app/core/uploads.py`, `validate_upload(file, kind=UploadKind.TEXT)` acepta `.md`/`.markdown`/`.txt` y rechaza binario disfrazado. No reimplementarla.

> **Dos reglas duras que atraviesan ING.0, VIS y RAG** (replanificación 2026-07-28): (1) el vocabulario de ámbitos/submaterias es **dato versionado en tabla**, nunca `Enum` ni `CheckConstraint` — está pendiente de validar por SG y debe seguir siendo revisable; (2) **la taxonomía no entra jamás en el texto embebido**, o cada revisión del vocabulario costaría un re-embedding del corpus completo. Los pares bilingües van al `tsvector` de RAG.4, no al embedding.

> Bloque 9R Redacción Contract-First cerrado: 9R.0→9R.10.2. Siguiente: Fase 10 (Plantillas y Temas).

**Orden de ejecución acordado (2026-05-13, actualizado 2026-07-15):**
`9R.7.1→9R.10` → `Fase 10` → `1C.0→1C.1` → `Fase 13 (NER redacción)` → `1C.2→1C.4` → `Fase 20 reducida` → `Bloque SBX (SBX.1→SBX.4)` → `Bloque 9Q (9Q.0→9Q.9)` → **`Bloque AUTH (AUTH.1→AUTH.4)`** → **`Bloque MCP (MCP.1→MCP.4)`** → **`Bloque ROL (ROL.1→ROL.2)`** → `Fase 11 (11.1→11.3)` → **`SEC.6`** (adelantado) → **`Bloque ING.0 (ING.0.1→ING.0.5)`** → *(carga del corpus v1 + pruebas manuales end-to-end)* → **`RAG.1`** (baseline) → **`Bloque TST (TST.1→TST.2)`** → **`RAG.2`** (consolidación de grafos) → **`Bloque VIS (VIS.1→VIS.3)`** → **`RAG.3→RAG.14`** → **`Bloque SYNC (SYNC.1→SYNC.2)`** → **`Bloque SEC (SEC.1, SEC.2, SEC.2.1, SEC.3, SEC.4, SEC.4.1, SEC.5, SEC.7)`** → **`Bloque CAL (CAL.1→CAL.5)`** → `Deploy GCP` (con corpus definitivo revisado) → **`Bloque OWUI (OWUI.1→OWUI.3)`** (post-deploy, spike/comparación para el piloto)

> **Actualización del orden 2026-07-28:** el Bloque RAG se **parte** para intercalar el Bloque VIS. `RAG.1` y `RAG.2` van delante (baseline sobre el corpus v1 y consolidación de grafos); `VIS.1→VIS.3` después, porque VIS.2 reescribe `md_agent_selector_pipeline` y hacerlo antes sería escribir contra `agent/graph.py`, que RAG.2 elimina. El resto del Bloque RAG (RAG.3→RAG.14) sigue sin cambios de alcance, con cuatro enmiendas in situ (RAG.2, RAG.4, RAG.5, RAG.7). El Deploy GCP pierde la fecha fija de septiembre: el usuario prioriza los fundamentos sobre el calendario (2026-07-28).

> **Actualización del orden 2026-07-11:** insertados **ROL** (antes de Fase 11), **SEC** (bloqueante, antes de Deploy) y **CAL** (antes de abrir el repo AGPLv3), a partir de `docs/VALORACION_PROYECTO.md`. **ING.0** (carga de corpus curado) es la vía de ingesta principal pero depende de que el usuario entregue la carpeta canónica + manifiesto; se ejecuta cuando esté listo, en paralelo. Total nuevos prompts Fase 1: +16 (ROL×2, SEC×7, CAL×5, ING.0×2).

> **Actualización del orden 2026-07-15:** nuevo **Bloque RAG** (RAG.1→RAG.14) en `Plan_TDD_Fase1.md`, derivado de la comparativa arquitectónica con LAMB (`docs/COMPARATIVA_RAG_LAMB.md`). Insertado **tras las pruebas manuales con corpus de prueba y antes del resto de SEC**: el corpus cargado en ING.0 es insumo del dataset dorado (RAG.1) y las mejoras de retrieval llegan al deploy de septiembre. Planificación en dos fases: relación de prompts aprobada y **2ª pasada de detalle verbatim completada el mismo día** (tests enumerados, ficheros, migraciones, criterio de done por prompt). Total nuevos prompts Fase 1: +14.

> **Bloque OWUI añadido (2026-07-24):** nuevo **Bloque OWUI** (OWUI.1→OWUI.3) al final de `Plan_TDD_Fase1.md`, **post-deploy**, desde `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md`. Es lo único que las decisiones (carcasa OWUI + dependencias RAG) exigían **añadir**: el bloque RAG ya estaba alineado y no se reescribe; la chat-UI React no se descoped (decisión del usuario). Contenido: **OWUI.1** adaptador `/v1/chat/completions`+`/v1/models` sobre el grafo (scope nuevo `chat:completions`, reusa CoreGraph, no reimplementa RAG); **OWUI.2** citas P6 + anonimización P7 con test de equivalencia vs `hub_chat`; **OWUI.3** Pipe delgado + despliegue edge (P8) + validación e2e. Regla dura: la gobernanza se hereda del grafo, nunca vive en el adaptador ni en el Pipe.

> **Lente de mantenibilidad del RAG (2026-07-24):** creado `docs/RAG_SUSTITUCION_DEPENDENCIAS.md` — vista transversal "código propio → dependencia madura" del Bloque RAG + Bloque ING, derivada de `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §6 (RAG/ingesta se queda en el perímetro; el mantenimiento se alivia apoyando las **primitivas** en librerías, no moviéndolas a OWUI). **No añade prompts**: reencuadra los ya aprobados. Clasificación: ✅ ya apoyado (chunker/embeddings/PDF), ♻️ reinventado→sustituir (ILIKE→FTS = RAG.4), ➕ hueco→añadir (HNSW=RAG.3, reranker=RAG.6, parent-child=RAG.8, multi-formato Docling=ING), 🔒 diferencial→no sustituir (`superseded`/citas/`hasher`/`quality`). 80 % del valor = **RAG.4 + RAG.6**. Anti-patrón: no adoptar LlamaIndex/Haystack como orquestador.

> **Actualización del orden 2026-07-13:** el usuario confirma que el **deploy no ocurrirá hasta septiembre** (a la espera de la revisión definitiva del corpus UJI) y quiere hacer **pruebas manuales + ingesta con un corpus de prueba en local** antes de esa fecha. Se **adelanta el Bloque ING.0** (antes backlog/"cuando el corpus esté listo") a justo después de cerrar Fase 11, usando un corpus de prueba no-regulatorio (sin bloqueo por revisión). Se adelanta también **SEC.6** (validación de subidas) delante de ING.0.2, que quiere reutilizarla, para no duplicar trabajo. El resto del Bloque SEC (SEC.1-5, SEC.7), CAL y Deploy GCP se mantienen en el orden previo, con margen hasta septiembre.

> **Adelanto AUTH+MCP (2026-06-11):** SSO SAML real (Subfase 1.B.1, antes diferida) + PAT para clientes máquina, insertados **antes de Fase 11** para habilitar el Bloque MCP (servidor stdio de autoría de plantillas y configuración de chatbots, `docs/mcp.md`). SAML autentica humanos; el PAT es lo que consume el servidor MCP headless. Total Fase 1: 55 → 63 prompts (+8: AUTH.1-4, MCP.1-4).

> **Bloque ING (Ingesta multi-formato) — planificado 2026-06-23:** detalle de las 4 fases y decisiones de diseño en el historial (2026-06-23). **Adelantado al orden de ejecución el 2026-07-13** (ver nota arriba) — ya no es backlog sin programar; se ejecuta con corpus de prueba tras cerrar Fase 11, antes de la carga definitiva de septiembre.

> Nota: el bloque **9R** se incorporó el 2026-05-11 a partir de `Rediseño_informes.md`.
> Sustituye los antiguos prompts 9.11a–9.11d. **Fase 13** en Fase 1 cubre únicamente el hook NER pre/post-LLM en DraftingCoreGraph; la integración con expedientes es Fase 3. **Fase 20** se ejecuta sin la consola conversacional admin (diferida a Fase 2). **Fase 11** precede a Deploy GCP como prerrequisito de distribución como software libre.

---

### Plan_TDD_Fase2.md y Plan_TDD_Fase3.md

| Plan | Estado |
|------|--------|
| Fase 2 — Migración NiceGUI + Agente local | ⏳ No iniciada — **replanteada 2026-07-11**: la migración en bloque NO se recomienda (gran parte del valor ya está en `redaccion`/`agents_hub` o superada por agentes IA). Se reduce de facto a **Subfase 2.A (Thin Client, infra para Fase 3)** + limpieza; el resto se migra por goteo bajo demanda del piloto. Ver §"Recomendaciones y replanteamiento" en Plan_TDD_Fase2.md |
| Fase 3 — Gestor de Expedientes | ⏳ No iniciada — **recomendaciones añadidas 2026-07-11** (prerrequisitos reconciliados, checkpointing oficial, auditoría inmutable con rol BD, RGPD en Fairness, reutilización de lo ya migrado, spike temprano ENI/ENS). Ver §"Recomendaciones de la Fase 3" en Plan_TDD_Fase3.md |

**Subfase 2.B — Estado del plan para el extractor PDF (9.12b / 9.13)**

Plan enriquecido el 2026-05-11 con el análisis de `Migración_extracción_pdf.txt`:

| Prompt | Descripción | Estado |
|--------|-------------|--------|
| 9.12b.0 | Auditoría funcional legacy (`legacy_extraction_spec.md`) | ⏳ Pendiente |
| 9.12b | Refactor backend PDF extractor a Docling | ⏳ Pendiente |
| 9.13 | UI React del extractor PDF (Focus Mode + wizard) | ⏳ Pendiente — bloqueado por 9.12b |

Secuencia de implementación: 12 pasos atómicos documentados en **Guía 9C.1** del plan.
Prompts verbatim para el agente: `Migración_extracción_pdf.txt` §5.

> **Prerequisito de Fase 2**: Subfase 1.A completada ✅ (9B.14 verde, 2026-05-11).

---

## Historial

Las entradas cerradas viven en **`HISTORIAL.md`**, en este mismo directorio. Se separaron el
2026-08-21: eran 535 de los 626 KB de este fichero, que se lee entero al arrancar cada sesión.

Al cerrar un prompt, **la fila nueva va arriba** de la tabla de `HISTORIAL.md`, con la fecha, el
identificador y una descripción de una línea. Este fichero conserva el cursor, los planes activos y
los bloques cerrados recientes.
