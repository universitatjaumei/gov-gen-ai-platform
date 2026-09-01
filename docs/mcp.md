# Valoración: configurar plantillas de informes vía MCP

**Fecha**: 2026-06-06
**Estado**: ✅ **PLANIFICADO (2026-06-11)** — convertido en el **Bloque MCP** (MCP.1–MCP.4) de
`planificacion/Plan_TDD_Fase1.md`, precedido por el **Bloque AUTH** (AUTH.1–AUTH.4) que adelanta el SSO SAML +
PAT. Decisiones: opción A (stdio), alcance completo (plantillas + chatbots + test_chat). Ver
`planificacion/PROJECT_STATE.md` → orden de ejecución.

**Veredicto corto: muy viable, encaja con la arquitectura existente y no requiere
reabrir nada de Fase 1.** La arquitectura contract-first hace casi todo el trabajo.

---

## Por qué encaja bien

1. **El problema real es de autoría, no de transporte.** Una `ReportTemplateSpec`
   (`server/app/modules/redaccion/contracts/template.py:120`) es un documento JSON
   complejo: 11 tipos de bloque con unión discriminada, `depends_on` entre bloques,
   refs `CHART/TABLE → DETERMINISTIC_DATA`, regla de `REVIEW_GATE`... Construir un
   editor visual completo para eso en React es caro; redactarlo con Claude Code
   contra el JSON Schema de Pydantic es exactamente el caso de uso fuerte de MCP.

2. **Las piezas críticas ya existen y no hay que tocarlas:**
   - `DraftValidator` (`server/app/modules/redaccion/services/draft_validator.py:33`)
     → se expone tal cual como tool `validate_template_draft`. Claude itera contra
     él antes de publicar.
   - Versionado append-only (`HubReportTemplateVersion`, sin `update()` en
     `ReportTemplateVersionRepo`) → un tool MCP nunca puede corromper una versión
     publicada; solo añade.
   - `ReportTemplateSpec.model_json_schema()` → se expone como **resource MCP**, y
     Claude redacta directamente contra el contrato. Cero duplicación de esquema.

3. **No viola la frontera edge/cloud.** El servidor MCP sería un *cliente más* de
   la API HTTP existente (`hub_redaccion_router`, `Deploy: edge`), igual que el
   frontend. No cruza bases ORM ni importa módulos prohibidos.

---

## Opciones de implementación

| | **A. MCP stdio local (wrapper de la API)** | **B. MCP montado en FastAPI (HTTP streamable)** |
|---|---|---|
| Qué es | Paquete pequeño (`mcp_server/` o script `uv run`) con el SDK oficial `mcp`, que llama a `/hub/redaccion/*` por HTTP | Endpoint `/mcp` montado en el propio servidor |
| Cambios en el server | **Cero** (salvo auth, ver abajo) | Nueva superficie, clasificación deploy, tests del transporte |
| Quién lo ejecuta | El admin/partner en su máquina, registrado en `claude mcp add` | Cualquier cliente MCP remoto |
| Riesgo | Mínimo | Medio (nueva superficie expuesta) |

**Recomendación: opción A para empezar.** Es ~1 prompt de trabajo, reversible, y
valida el caso de uso antes de comprometerse con MCP remoto.

---

## Puntos que requieren decisión de diseño

### 1. Auth para clientes máquina

Hoy solo hay JWT de sesión con expiración
(`server/app/core/auth/jwt_handler.py`, claims `sub/email/role/exp`). Un servidor
MCP necesita o bien un token de larga duración o un **PAT (personal access token)**
revocable con rol admin/partner. Es el único desarrollo backend real que pediría la
opción A.

### 2. Regla dura nº 4 de `REDACCION_CONTRACT_FIRST.md`

> "El LLM no puede crear plantillas persistentes sin aprobación HITL."

Con MCP el humano **sí** está en el bucle (el usuario de Claude Code aprueba cada
tool call), pero conviene reforzarlo en el diseño: tools de lectura/validación
libres, y el tool `publish_template_version` como única operación de escritura —
idealmente devolviendo el resultado del validador y exigiendo un flag explícito de
confirmación. Así la regla se cumple por construcción, con el admin como aprobador.

---

## Toolset mínimo propuesto

- **Resources**: JSON Schema de `ReportTemplateSpec`, registry de profiles válidos
- **Tools (lectura)**: `list_templates`, `get_template_spec(version_id)`
- **Tools (validación)**: `validate_template_draft(spec)` — sin persistir
- **Tools (escritura)**: `create_template(draft)`,
  `publish_template_version(template_id, spec)` — restringidos a admin/partner vía PAT

---

## Recomendación de planificación

**No bloquear el cierre de Fase 1 con esto.** Nada de lo desarrollado necesita
cambiar para soportarlo después — el contract-first ya da la compatibilidad gratis.
Encuadrarlo como un prompt nuevo (¿9R.11 o inicio de Fase 2?): *"Servidor MCP stdio
para autoría de plantillas + PAT para clientes máquina"*. Modelo sugerido: Sonnet
(alcance cerrado, contratos ya definidos).

---

---

# Valoración 2: creación y definición de chatbots de información vía MCP

**Fecha**: 2026-06-06

**Veredicto corto: viable y con sinergia directa con la valoración 1 (mismo servidor
MCP, misma auth PAT), pero el caso de uso es distinto y más acotado de lo que parece.**
La distinción clave: en chatbots, los grafos y sus fases **no son datos configurables,
son código** — y para el código ya existe Claude Code sin necesidad de MCP.

---

## La distinción central: dato vs. código

| Qué | Naturaleza | Cómo lo toca Claude |
|---|---|---|
| Instancia de chatbot (`HubChatbot`: retrieval_mode, top_k, system_prompt, umbrales, profile) | **Dato** (fila en BD) | **MCP** → API cloud |
| Prompts (`HubPromptTemplate`, system_prompt) | **Dato** (texto rico) | **MCP** — caso de uso fuerte |
| Jerarquía router→hijos | **Dato** (relaciones) | **MCP** |
| Fases del grafo (`detect_language → retrieve → merge → quality_gate → generate/fallback`) | **Código** (`CoreGraph`, `core_graph.py:54-109`) | Claude Code editando el repo, sin MCP |
| Nuevo perfil de grafo o nueva estrategia de retrieval | **Código** (registry + factory, `GRAPH_PROFILES.md`) | Claude Code editando el repo, sin MCP |

A diferencia de `ReportTemplateSpec` (documento JSON complejo que se *redacta*), la
config de un chatbot son campos escalares + enums (`public_graph_profile` ∈ 3 valores,
`retrieval_mode` ∈ 3 valores). El grafo es deliberadamente **hardcoded con estrategias
inyectadas** — un buen diseño que NO conviene convertir en "grafo como JSON" solo para
hacerlo editable por MCP. Eso sería una re-arquitectura mayor sin demanda real.

## Dónde está el valor real de MCP en chatbots

No en "rellenar campos" (la UI ya lo hace bien), sino en **flujos asistidos que la UI
no puede hacer**:

1. **Configuración informada por el corpus.** `GET /hub/chatbots/{id}/corpus-stats`
   ya devuelve modo recomendado según tokens (`hub_chatbots_router.py:254-257`).
   Claude vía MCP puede: analizar el corpus → elegir `retrieval_mode` → ajustar
   `top_k`/umbrales → justificar la decisión. Es consultoría de configuración, no CRUD.
2. **Autoría y refinado de prompts.** `system_prompt` y `HubPromptTemplate` por
   idioma/slug: el mismo caso fuerte que las plantillas de informes.
3. **Bucle configurar → probar → ajustar.** Si se expone también un tool de chat de
   prueba (`hub_chat`, edge), Claude puede lanzar preguntas de evaluación contra el bot
   recién configurado y ajustar umbrales/prompt iterativamente. Esto es lo que ningún
   formulario ofrece. *Nota: en dev (`DEPLOY_MODE=all`) chat y config conviven en el
   mismo server; en despliegue real son superficies distintas (edge vs cloud).*
4. **Diseño de portales jerárquicos.** Componer router + hijos con las validaciones
   existentes (máx. 2 niveles, mismo client, router sin hijos router).

## Diferencias de riesgo respecto a plantillas

| Aspecto | Plantillas (redaccion) | Chatbots (agents_hub) |
|---|---|---|
| Frontera deploy | Edge | **Cloud** (`hub_chatbots_router`, roles admin/partner) — coherente: configurar es trabajo del cloud |
| Versionado | Append-only (a prueba de errores) | **In-place, sin historial** — un PATCH erróneo muta un bot en producción sin rollback |
| Impacto inmediato | Workspace ancla versión; migración explícita | **El widget público cambia al instante** |
| Validación | `DraftValidator` dedicado | Repartida: CHECK constraints + validaciones en endpoint (límite 128K para MD_LONG_CONTEXT, reglas de jerarquía) — el wrapper MCP las hereda al llamar por HTTP |

El riesgo dominante es la **mutación in-place sobre bots en producción**. Mitigaciones
ordenadas de menor a mayor coste:

1. Tool `update_chatbot` con eco de diff (config actual → propuesta) antes de aplicar,
   apoyado en el permission prompt de Claude Code como HITL.
2. Parámetro `dry_run` que devuelva el resultado de validaciones sin persistir.
3. (Solo si se demanda) snapshot/audit-log ligero de config previa al PATCH. **No**
   replicar el versionado append-only de redaccion sin necesidad demostrada.

## Toolset propuesto (namespace `chatbots_*`, mismo servidor MCP)

- **Resources**: enums válidos (profiles, retrieval_modes, kinds), JSON Schema de
  `ChatbotCreate`/`ChatbotUpdate`, contenido de `GRAPH_PROFILES.md` como guía
- **Lectura**: `list_clients`, `list_chatbots`, `get_chatbot`, `get_corpus_stats`,
  `list_prompt_templates`
- **Escritura**: `create_chatbot`, `update_chatbot` (con diff/dry_run),
  `update_prompt_template`, `assign_child` / `unassign_child`
- **Opcional fase 2**: `test_chat(chatbot_id, message)` para el bucle de evaluación

## Sinergia y planificación

- El coste incremental sobre la valoración 1 es bajo: misma infraestructura (servidor
  MCP stdio, PAT, registro en `claude mcp add`), segundo namespace de tools.
- Prerequisito compartido: **PAT para clientes máquina** (sigue siendo el único
  desarrollo backend real).
- Lo que NO requiere MCP: nuevos perfiles de grafo, nuevas estrategias, cambios de
  fases — eso es desarrollo sobre el repo y ya está cubierto por Claude Code +
  `GRAPH_PROFILES.md`.
- Deuda detectada de paso (independiente de MCP): `edge_sync` son stubs
  (`api/v1/edge_sync.py:60-69`) y no existe un doc de contrato de chatbots equivalente
  a `REDACCION_CONTRACT_FIRST.md`.

---

## Aspectos pendientes de ampliar

> **Actualización 2026-08-31**: la **opción B** (MCP remoto por HTTP streamable) dejó de ser
> futurible: tiene caso de uso — que agentes externos (Claude Cowork, Copilot…) registren su
> actividad y usen la anonimización — y prompts redactados en el **Bloque REG** de
> `planificacion/Plan_TDD_Fase1.md` (REG.4). Valoración completa en
> `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md`.

<!-- Sección reservada para la ampliación del usuario -->
