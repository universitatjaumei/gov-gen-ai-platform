# Pruebas manuales de la plataforma completa

**Prompt MAN.1** (`Plan_TDD_Fase1.md`). Sustituye al modelo anterior de un `.bat` por bloque:
esos guiones caducaban en silencio cada vez que un bloque posterior renombraba una ruta o
rehacía una pantalla, y nadie había recorrido la plataforma de una pieza.

**Regla que no cambia** (CLAUDE.md §Verificación de UI): lo que el agente puede comprobar en
navegador **no entra** aquí. Esta matriz es sólo lo irreducible — credenciales e IdP reales,
sistemas externos no simulables, juicio subjetivo, lector de pantalla real y datos personales
de verdad.

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

**Hallazgos de esta sesión** (no son "irreducibles": son código a corregir, no trabajo para el
usuario). Documentados en el informe de cierre del bloque, no aquí.

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
