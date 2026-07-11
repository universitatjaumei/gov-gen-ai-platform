# Plan TDD — Fase 3: Gestor de Expedientes e Integración Institucional

> Actualizado: 2026-05-04. Generado dividiendo `PLAN_TDD_DETALLADO.md` en tres archivos por fase funcional.

## Propósito
Fase 3 del plan de desarrollo de Gov Gen AI Platform. Implementa el módulo de tramitación
administrativa multi-fase con LangGraph y checkpointing en PostgreSQL, auditoría conforme al
Reglamento de IA (RIA) y los adaptadores de integración con los sistemas institucionales
(UJI, Gestión 400, ENI/ENS).

## Prerrequisito
- Fase 2 completada (Thin Client operativo, MCP Client disponible).
- Auth OIDC/SAML activo (Subfase 1.B).

## Alcance
- **Subfase 3.A:** Schema BD y motor LangGraph con checkpointing (Prompts E1, E2).
- **Subfase 3.B:** AuditService RIA (E3) + Frontend expedientes (E4) + Agente Analista (FASE 17) + Prompts nuevos (Snapshots, Fairness).
- **Subfase 3.C:** Adaptadores UJI, Gestión 400, capa ENI/ENS (E5, FASE 19).
- **Al finalizar F3:** Despliegue Edge node híbrido GCP (Prompt D.6).
- **Diferido post-cloud:** Microservicios Embedding + Docling (FASE 22).

"Directrices para detallar el TDD de la Fase 3 (Expedientes, HATEOAS y LangGraph)"

Para la orquestación de expedientes y su interfaz, debes imponer un diseño HATEOAS estricto para la UI y contratos rígidos para LangGraph.

Para el Motor Backend (Prompt E2):

El DTO de respuesta de un expediente (ExpedienteResponse) DEBE incluir un campo calculado en el servidor llamado acciones_permitidas: list[str] (ej. ["avanzar", "rechazar"]).

El backend calcula este array evaluando la fase_actual, el estado del expediente, y cruzándolo con el responsable_rol definido en acciones_fase frente al usuario que hace la petición.

En el TDD (RED): Escribe tests de backend que aseguren que si un usuario sin rol consulta el expediente, acciones_permitidas llega vacío, sin importar la fase.

Para el Frontend (Prompt E4):

En ExpedienteDetailPage.tsx y AprobacionesBandejaPage.tsx, los botones de acción se renderizan iterando EXCLUSIVAMENTE sobre el array acciones_permitidas.

En el TDD (RED): Escribe un test que verifique que el frontend no contiene lógica de negocio del tipo if (fase === 'revision') showButton().

Para los Nodos LangGraph:

El ExpedienteState es sagrado. Al redactar los tests de los nodos (NodoLLM, NodoAnalista), exige que el test falle si el nodo intenta mutar el estado fuera de los campos tipados o si intenta devolver datos en un formato distinto al esperado por el contrato del nodo siguiente.

## Prompts con TDD por detallar antes de ejecutar

### Prompts ya descritos en este documento (arquitectura definida, TDD pendiente)
- **FASE 17** (Agente Analista + base vectorial de normativa)
- **FASE 19** (Los prompts TDD detallados están ya en el Prompt E5 de FASE 12)

### Prompts adicionales previstos (anotados al final de cada subfase)
Los siguientes prompts han sido identificados en la planificación pero sus prompts TDD
no se desarrollarán hasta comenzar la subfase correspondiente:

| ID tentativo | Subfase | Descripción |
|---|---|---|
| 3B.5 | 3.B | Snapshots Administrativos: histórico de KB con `as_of_date` |
| 3B.6 | 3.B | Dashboard de Sesgo y Equidad — Fairness Audit (RIA Art. 13) |
| 3C.0 | 3.C | Ejecución Edge en tramitación: invariante arquitectónico |

---

# Recomendaciones de la Fase 3 (2026-07-11)

> Sección añadida a partir de `VALORACION_PROYECTO.md`. **Precede y condiciona** a los sprints
> E1–E5, FASE 17 y 19 de más abajo. No borra prompts: reconcilia los prerrequisitos con el estado
> real del proyecto y añade recomendaciones técnicas y de riesgo. Léela antes de detallar el TDD
> de cualquier sprint de Fase 3.

## 1. Prerrequisitos actualizados (reconciliación con el estado real)

Los prerrequisitos escritos en este documento ("Auth OIDC/SAML activo", "MCP Client", etc.) se redactaron antes de cerrar la Fase 1. Estado real y ajustes:

- **Autenticación**: NO existe OIDC; existe **SAML 2.0 + JWT + PAT** (Bloque AUTH de Fase 1, ya cerrado). Es suficiente para el modo identificado. Sustituir "OIDC/SAML" por "SAML/JWT" en los prerrequisitos de E1/E2/E4.
- **Aislamiento multi-tenant (crítico para expedientes)**: los expedientes contienen datos personales sensibles del ciudadano. El aislamiento por organización se implementa en Fase 1 (**Bloque SEC, prompt SEC.2**: claim `organizacion_ids` + `assert_org_access`/`scope_query_to_orgs` + gate de CI). **Todos los endpoints de expedientes (E1, E2, E4) deben pasar por esa capa desde el diseño**, no redescubrirla. Añadir a los tests de E1/E2 casos de aislamiento por organización (un Admin de la organización A no ve/tramita expedientes de la B).
- **Nomenclatura institucional**: usar la nueva, ya aplicada en Fase 1 (Bloque ROL): roles `superadmin`/`admin`/`user`, entidad `HubOrganizacion`, FK `organizacion_id`. Los `tipos_expediente`/`acciones_fase` declaran `responsable_rol` contra esos roles. Sustituir cualquier referencia a `client_id`/`partner`.
- **Thin Client + Sandbox (Subfase 2.A)** es prerrequisito de `NodoScript` y `NodoRPA`: el replanteamiento de Fase 2 (2026-07-11) **mantiene 2.A** precisamente porque la Fase 3 la necesita. `NodoScript`/`NodoRPA` **delegan la ejecución al Edge** (invariante 3C.0); el cloud recibe el resultado, nunca el documento original.
- **MCP Client (2C.0)** es prerrequisito bloqueante de la Subfase 3.C (adaptadores). Recomendación de Fase 2: adelantarlo al inicio de 2.C. Confirmar que está operativo antes de abrir E5.

## 2. Recomendaciones técnicas por sprint

- **E2 — Checkpointing**: NO implementar a mano la tabla `langgraph_checkpoints`. Usar el saver oficial **`langgraph-checkpoint-postgres`** (`AsyncPostgresSaver`): menos código, compatibilidad garantizada con `interrupt()`/resume (justo lo que necesita el `NodoHuman`) y con el versionado de LangGraph. Solo justificar tabla propia si hay un requisito que el saver oficial no cubra.
- **E3 — Log de auditoría realmente inmutable**: proteger `audit_expediente` no solo por ausencia de endpoints UPDATE/DELETE (control débil, saltable por cualquier bug o acceso directo), sino con **defensa en profundidad**: (a) rol de BD de la aplicación **sin privilegio UPDATE/DELETE** sobre esa tabla (solo INSERT/SELECT); (b) **anclaje periódico del hash de cabeza** de la cadena (p.ej. sellado diario) para detectar manipulación retroactiva. Añadir un test que verifique que la app no puede mutar ni borrar filas de la tabla de auditoría.
- **3B.6 — Fairness Audit (RGPD antes que código)**: definir **qué metadatos de colectivo se capturan y con qué base jurídica RGPD** ANTES de implementar el `FairnessScore`. Sin esa definición el dashboard no tiene datos que agrupar, y capturar datos de colectivo protegido sin base legal es un riesgo mayor que el que la métrica pretende mitigar. Documentar la base jurídica y la minimización como parte del prompt, no como añadido.
- **3B.5 — Snapshots (`as_of_date`)**: apoyarse en la **procedencia del corpus** ya definida en Fase 1 (`CorpusManifest`/`CorpusDocumentEntry` de ING.0.1 ya prevé `valid_from`/`valid_to`). El snapshot de KB normativa se construye sobre esos campos, no sobre una vigencia inventada en Fase 3. Conectar ambos: el corpus `regulation` se ingiere con vigencia; el retriever la filtra por fecha.

## 3. Reutilización de lo ya construido (no reimplementar)

Varios componentes que los sprints de Fase 3 dan por construir **ya existen** tras Fase 1:

- **`NodoScript`/`NodoValidador`** reutilizan el `ScriptSecurityAuditor` (auditoría AST, `redaccion/services/script_auditor.py`) y el `sandbox_client` (microservicio Docker, `core/sandbox_client.py`) ya migrados. No reimplementar la auditoría ni el sandbox por proceso legacy.
- **`NodoAnalista` (3B.1)** reutiliza el retriever de `agents_hub` + la KB `regulation` ingerida vía **corpus curado (Bloque ING.0)** con citas trazables (`source_url` en `HubDocument`). La normativa con procedencia y revisión humana es justo lo que exige la fiabilidad jurídica de un expediente.
- **Anonimización/Vault**: el motor NER reversible existe (Fase 13); el Vault Edge se completa en 2.A.4/2.A.5. Los expedientes marcados sensibles fuerzan anonimización (política `HubTipoExpediente.requires_anonymization`, §7.2 Arquitectura). No reescribir el motor.
- **Export/RunManifest**: el `export_service` (DOCX) y el `DraftingRunManifest` existen; el informe RIA de E3 extiende ese manifiesto con el *Learning Trace*, no crea uno nuevo.

## 4. Riesgo dominante: dependencia institucional externa (E5 / FASE 19)

La Subfase 3.C (AdaptadorUJI, AdaptadorGestion400, capa ENI/ENS) es la de **mayor incertidumbre, y NO es de código**: depende de conseguir credenciales, entornos de prueba y las especificaciones reales (DIR3, eEMGDE, formatos CSV, XSD de evidencia ENI) de sistemas de terceros. Recomendación:

- **Spike temprano al inicio de la Fase 3**, no al final (E5): confirmar acceso real a las APIs de UJI y Gestión 400 y a las specs ENI/ENS. Si el acceso o la documentación no están disponibles, se sabe pronto y no bloquea el resto.
- **El `AdaptadorNativo` (E1) permite avanzar todo el motor** (E2/E3/E4) sin depender de sistemas externos. Diseñar E1–E4 para que funcionen end-to-end en modo nativo; los adaptadores externos (E5) se enchufan cuando el acceso institucional llegue.
- **Confirmar un caso/institución comprometido** antes de invertir las ~9-10 semanas de Fase 3: es un producto distinto (tramitación) con dependencias externas fuertes; conviene un tipo de expediente piloto real acordado con UJI antes de empezar.

---

## FASE 12: Gestor de Expedientes (Integración vía MCP)

> **Arquitectura MCP**: La integración con el Gestor de Expedientes legacy se realizará exponiendo dicho sistema como un Servidor MCP (Model Context Protocol) que GovGenAI consumirá como cliente agnóstico. Esto aísla la plataforma de las especificidades del sistema antiguo.

**Objetivo de la Fase**: Implementar el módulo de gestión de tramitaciones administrativas multi-fase,
auditables y conformes con el Reglamento de IA de la UE (RIA).

**Dependencias**: Fase 3 (Docling), Fase 4 (LangGraph operativo), Fase 5 (Auth OIDC/SAML del PLAN_DESARROLLO.md)

**Contexto**: El Gestor de Expedientes es el tercer módulo de la plataforma. Reutiliza la infraestructura
del Hub (LangGraph, Docling, pgvector) y el patrón de metaprogramación de Automation para orquestar
tramitaciones administrativas. Ver sección 9 de modulo_AI_agents-hub.md para el diseño completo.

**Mapa de sprints**:

| Sprint | Contenido | Duración | Prerequisito |
|--------|-----------|----------|--------------|
| E1 | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Hub infrastructure |
| E2 | Motor LangGraph con checkpointing, nodos estándar, AdaptadorREST | 2 semanas | LangGraph Hub operativo |
| E3 | AuditService, ExplicabilidadService, endpoint /informe, tests RIA | 1 semana | Sprint E2 |
| E4 | Frontend React: lista, detalle, bandeja aprobaciones, configurador | 3 semanas | Auth OIDC/SAML, Sprint E2 |
| E5 | AdaptadorOracle via MCP Client, sincronizacion bidireccional | 1 semana | MCP Client (Fase 5 PLAN_DESARROLLO) |

---

### Prompt E1 - Schema de Base de Datos y API Base del Gestor (TDD RED/GREEN)

**Objetivo**: Crear las tablas del Gestor de Expedientes y los endpoints CRUD básicos.

**Instrucciones**:

```
Actua como experto en FastAPI y SQLAlchemy async. Implementa el modulo base del Gestor de Expedientes
en server/app/modules/expedientes/.

TABLAS NUEVAS (migration Alembic):
- tipos_expediente: catalogo de tramitaciones (id, nombre, descripcion, version, configuracion JSON)
- expedientes: instancias (id, tipo_id, estado, tenant_id, creado_por, fecha_inicio, metadata JSON)
- fases_expediente: (id, expediente_id, nombre, estado, orden, funcion, responsable_rol)
- acciones_fase: (id, fase_id, tipo [llm|script|human|rpa|api_externa], funcion, responsable_rol, configuracion JSON)
- ejecuciones_accion: (id, accion_id, expediente_id, timestamp, actor_id, resultado, codigo_ejecutado, explicacion, estado)
- documentos_expediente: (id, expediente_id, nombre, tipo, doc_chunk_id nullable, ruta, metadata)
- audit_expediente: log inmutable (id, expediente_id, fase_id, accion_id, timestamp, actor,
  accion_descripcion, estado_anterior, estado_nuevo, hash_integridad)

ENDPOINTS (bajo /expedientes):
GET    /expedientes/tipos/
GET    /expedientes/tipos/{tipo_id}
POST   /expedientes/
GET    /expedientes/
GET    /expedientes/{id}
DELETE /expedientes/{id}
GET    /expedientes/pendientes/mios
GET    /expedientes/pendientes/rol/{rol}

TESTS REQUERIDOS:
- test_crear_tipo_expediente_con_fases_y_responsables
- test_crear_expediente_instancia
- test_listar_expedientes_filtrados_por_estado
- test_eliminar_expediente_solo_si_estado_inicial
- test_listar_pendientes_del_usuario_autenticado

CRITERIOS DE ACEPTACION:
- Todo tipo de expediente debe declarar funcion y responsable_rol en cada fase (obligatorio)
- Sin ellos, el tipo no puede activarse
```

---

### Prompt E2 - Motor LangGraph con Checkpointing (TDD RED/GREEN)

**Objetivo**: Implementar el motor de procesos basado en LangGraph con estado persistido en PostgreSQL.

**Instrucciones**:

```
Actua como experto en LangGraph y FastAPI async. Implementa el motor de procesos del Gestor
en server/app/modules/expedientes/engine/.

ESTADO DEL EXPEDIENTE (ExpedienteState):
class ExpedienteState(TypedDict):
    expediente_id: str
    tipo: str
    fase_actual: str
    datos: dict
    documentos: list[str]
    historial_acciones: list
    pendiente_humano: bool
    responsable_actual: str
    explicacion_ia: str

NODOS ESTANDAR A IMPLEMENTAR:
- NodoLLM: genera propuesta usando LLM Gateway existente
- NodoScript: ejecuta script Python determinista (reutiliza sandbox de Automation)
- NodoHuman: breakpoint LangGraph — el expediente queda suspendido esperando aprobacion
- NodoRPA: despacha job al agente de ejecucion local (Prompt 9.17)
- NodoAPIExterna: llama al MCP Client (cuando este disponible)
- NodoNotificacion: encola notificacion al responsable de la siguiente fase

CHECKPOINTING:
- Persistir estado del grafo en PostgreSQL (tabla langgraph_checkpoints)
- Permitir reanudar un expediente suspendido desde el punto exacto de parada

NUEVOS ENDPOINTS:
POST /expedientes/{id}/avanzar    -> ejecutar siguiente accion automatica
POST /expedientes/{id}/aprobar    -> resolucion humana positiva (NodoHuman)
POST /expedientes/{id}/rechazar   -> resolucion humana negativa + motivo
GET  /expedientes/{id}/pendiente  -> accion pendiente actual

TESTS REQUERIDOS:
- test_nodo_llm_genera_propuesta_y_guarda_explicacion
- test_nodo_human_suspende_grafo_y_espera
- test_aprobar_expediente_reanuda_grafo
- test_rechazar_expediente_registra_motivo_en_audit
- test_checkpointing_restaura_estado_tras_reinicio
```

---

### Prompt E3 - AuditService y Cumplimiento RIA (TDD RED/GREEN)

**Objetivo**: Implementar el log de auditoria inmutable y el endpoint de informe de trazabilidad.

**Instrucciones**:

```
Implementa AuditService en server/app/modules/expedientes/services/audit_service.py.

REQUISITOS:
1. Cada transicion de estado escribe una entrada en audit_expediente con hash de integridad
   (SHA-256 del contenido + timestamp + hash anterior -> cadena de bloques ligera)
2. El log es inmutable: ningun endpoint permite UPDATE o DELETE en audit_expediente
3. Endpoint GET /expedientes/{id}/audit -> log completo ordenado por timestamp
4. Endpoint GET /expedientes/{id}/informe -> PDF de trazabilidad completa para auditorias RIA

CAMPOS OBLIGATORIOS EN CADA ENTRADA:
- explicacion_ia: el "por que" de la decision (Art. 13 RIA — transparencia)
- codigo_ejecutado: el script exacto que se ejecuto (si aplica)
- actor: usuario o sistema que realizo la accion
- hash_integridad: SHA-256 encadenado

TESTS REQUERIDOS:
- test_audit_entry_created_on_every_state_transition
- test_audit_hash_chain_is_valid
- test_audit_log_is_immutable
- test_informe_pdf_contains_all_phases_and_decisions
- test_explicacion_ia_is_required_for_llm_nodes
```

---

### Prompt E4 - Frontend React: Pantallas del Gestor de Expedientes (TDD RED/GREEN)

**Objetivo**: Implementar las pantallas del Gestor en frontend/src/expedientes/.

**Instrucciones**:

```
Actua como experto en React + Tailwind. Implementa las pantallas del Gestor de Expedientes.

PANTALLAS A CREAR:
1. ExpedientesListPage.tsx — lista con filtros por estado, tipo y responsable
2. ExpedienteDetailPage.tsx — timeline de fases, documentos adjuntos, log de audit
3. AprobacionesBandejaPage.tsx — bandeja de expedientes pendientes del usuario autenticado
   con botones Aprobar / Rechazar + campo de motivo
4. TipoExpedienteConfigPage.tsx — formulario estructurado para definir tipos:
   fases, acciones, funcion y responsable de cada una
   (el disenador visual low-code queda diferido a v2)

REQUISITOS TRANSVERSALES:
- Todas las pantallas requieren autenticacion (OIDC/SAML activo)
- Los botones de accion se muestran solo al responsable de la fase actual
- Timeline visual del estado (pendiente / en_curso / aprobada / rechazada)

TESTS REQUERIDOS (Vitest):
- should_display_expedientes_with_filters
- should_show_approve_button_only_to_responsible_user
- should_render_audit_timeline_in_correct_order
- should_validate_tipo_form_requires_funcion_and_responsable
```

---

### Prompt E5 - AdaptadorUJI + AdaptadorGestion400 + capa ENI/ENS (TDD RED/GREEN)

**Objetivo**: Implementar los adaptadores de tramitación para los dos sistemas destino del piloto (UJI y Gestión 400) y la capa transversal ENI/ENS. Reemplaza el `AdaptadorOracle` descartado en la decisión 11 de `PLAN_DESARROLLO.md`.
**Prerequisito**: MCP Client operativo (Fase 5 de PLAN_DESARROLLO.md), sprints E2/E2.5/E2.6 completados.

**Instrucciones**:

```
Implementa en server/app/modules/expedientes/adapters/:

1. INTERFAZ COMÚN AdaptadorTramitacion (Protocol):
   async def consultar_expediente(self, ref_externa: str) -> dict
   async def crear_tramitacion(self, tipo: str, datos: dict) -> str
   async def actualizar_estado(self, ref_externa: str, estado: dict) -> bool
   async def adjuntar_documento(self, ref_externa: str, doc: bytes, meta: dict) -> bool
   async def publicar_resolucion(self, ref_externa: str, resolucion: dict) -> bool
   async def obtener_documentos(self, ref_externa: str) -> list[bytes]

2. AdaptadorUJI (uji_adapter.py):
   - Cliente HTTP contra el API institucional de la Universitat Jaume I
   - Autenticación: token institucional (via MCP Client)
   - Configurado por tipo de expediente, no globalmente

3. AdaptadorGestion400 (gestion400_adapter.py):
   - Cliente contra el API público de Gestión 400 (opensea)
   - Mapeo de esquemas: expediente interno ↔ formato G400
   - Detección de discordancias via BridgeService (Fase 6.6)

4. CAPA ENI TRANSVERSAL (eni_layer.py):
   - Resolvedor DIR3: valida/enriquece códigos de unidades administrativas
   - Enriquecedor eEMGDE: metadatos de gestión de documentos
   - Generador/verificador CSV (Código Seguro de Verificación)
   - Empaquetador de evidencia: conjunto de documentos + metadatos ENI

5. CAPA ENS (ens_policy.py):
   - Política por tipo de expediente: categorización alta/media/baja
   - Aplicada al sandbox (Fase 5.4) + AuditService (Fase 6.2)

NUEVOS ENDPOINTS:
POST /expedientes/{id}/sincronizar   -> pull del estado desde el sistema origen
POST /expedientes/{id}/publicar      -> push de la resolución al sistema origen
GET  /expedientes/{id}/evidencia-eni -> genera el paquete de evidencia ENI

TESTS REQUERIDOS:
- test_adaptador_uji_consulta_expediente_real (mock HTTP)
- test_adaptador_gestion400_mapea_esquema_bidireccional
- test_capa_eni_enriquece_metadatos_eemgde
- test_csv_generado_supera_verificacion_propia
- test_ens_categoria_alta_activa_sandbox_estricto
- test_adaptador_activo_se_configura_por_tipo_no_globalmente
- test_flujo_completo_consulta_proceso_publicacion_mock (E2E)
- test_serializacion_eni_valida_contra_xsd
```

---


---

## FASE 17: Agente Analista + Base Vectorial de Normativa

**Tipo**: Nuevo desarrollo  
**Prerequisitos**: FASE 12.E2 (motor LangGraph), FASE 3 (ingestión Docling)  
**Corresponde a**: Fase 7.E2.5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Añadir un nodo LangGraph previo al enrutado que clasifica la intención del tramitador e identifica la normativa aplicable, devolviendo citas trazables al nodo siguiente.

**Capacidades clave**:
- Knowledge base `regulation` (tipo nuevo) ingerida por Docling: BOE, DOGC, ordenanzas UJI, normativa autonómica y local relevante
- `NodoAnalista`: clasifica intención + recupera normativa aplicable por RAG sobre `regulation` KB
- Output del nodo alimenta al siguiente nodo (LLM o Script) como contexto + citas normativas con referencia trazable
- Solo para el grafo de expedientes; el chatbot informativo no usa este nodo

**Tests requeridos**: clasificación correcta en golden-set de peticiones, normativa devuelta con referencia trazable, nodo no invocado en grafo de chatbot informativo

---


> **Nota:** Los prompts TDD atómicos de esta fase se detallarán antes de ejecutar la Subfase 3.B.


---

## Subfase 3.B — Prompts adicionales previstos (sin TDD desarrollado)

> Estos prompts completan la Subfase 3.B con las capacidades de cumplimiento normativo
> y equidad en IA. Sus prompts TDD atómicos se detallarán antes de comenzar su ejecución.

---

### [3B.5] Snapshots Administrativos: histórico de Knowledge Base

**Objetivo funcional:** Añadir a los modelos de documentos KB los campos `valid_from` /
`valid_to` y una tabla `HubKnowledgeSnapshot` que capture el estado de la base de
conocimiento en un instante dado. Modificar el retriever para aceptar un parámetro
opcional `as_of_date` que filtre los documentos por su rango de vigencia normativa en
el momento de la consulta.

**Problema que resuelve:** Un expediente iniciado hace seis meses debe resolverse
aplicando la normativa vigente en ese momento, no la normativa actual. Sin snapshots
temporales, el sistema aplica siempre la última versión de la KB y no puede garantizar
coherencia jurídica en expedientes históricos, lo que viola el principio de seguridad
jurídica del derecho administrativo español (Ley 39/2015). La resolución de un
expediente pasado con normativa nueva puede constituir vicio de anulabilidad.

**Dependencias:** FASE 12.E2 (motor LangGraph con checkpointing que almacena la fecha
de inicio del expediente) · FASE 17 (base vectorial de normativa con documentos
versionados) · Retriever de Fase 1 base (VectorRetrievalStrategy y AgenticRetrievalStrategy).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 3.B.

---

### [3B.6] Dashboard de Sesgo y Equidad — Fairness Audit (RIA Art. 13)

**Objetivo funcional:** Extender las métricas RAGAS con un `FairnessScore` que analice
las interacciones de expedientes agrupadas por metadatos (colectivo, tipo de trámite,
unidad administrativa) y detecte tasas de éxito o tonos de respuesta estadísticamente
dispares entre grupos. Integrar la validación automática de sesgo en expedientes de
alto riesgo antes de la firma del informe final.

**Problema que resuelve:** El Reglamento de IA de la UE (Art. 13, requisito de
transparencia; Art. 9, sistema de gestión de riesgos) exige que los sistemas de IA de
alto riesgo demuestren activamente ausencia de discriminación. Sin métricas de equidad
trazables, la plataforma no puede acreditar conformidad RIA ante una auditoría
administrativa o judicial, lo que bloquea su uso en trámites administrativos sensibles
o con impacto en derechos de los ciudadanos.

**Dependencias:** FASE 12.E3 (AuditService con log inmutable de interacciones por
expediente) · FASE 17 (NodoAnalista, cuyos outputs son el sujeto principal del análisis
de sesgo) · HubInteraction de Fase 1 base (para histórico de interacciones de chatbots).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 3.B.

---

## FASE 19: Adaptadores UJI + Gestión 400 + Capa ENI/ENS (Servidores MCP)

> **Arquitectura MCP**: Se desarrollarán Servidores MCP para UJI, Gestión 400 y ENI/ENS, estandarizando la integración con la capa de inteligencia artificial.

**Tipo**: Nuevo desarrollo  
**Prerequisitos**: FASE 5 (MCP Client), FASE 12.E2 (motor LangGraph), FASE 14 (sandbox), FASE 18 (bridges)  
**Corresponde a**: Fase 7.E5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

> Los prompts detallados de esta fase están en la Fase 12, Prompt E5 de este documento.

**Objetivo**: Implementar los dos adaptadores del piloto v1 y la capa transversal ENI/ENS. Reemplaza el `AdaptadorOracle` descartado.

**Ver**: Fase 12, Prompt E5 de este documento (ya actualizado con este contenido).

---


> **Nota:** Los prompts TDD detallados están en el Prompt E5 de la FASE 12 de este documento.


---

## Subfase 3.C — Nota arquitectónica: ejecución Edge en tramitación

> Esta nota documenta un invariante que deben respetar todos los prompts de la
> Subfase 3.C. No es un prompt ejecutable.

### [3C.0] Invariante de ejecución Edge en tramitación de expedientes

**Objetivo funcional:** Establecer y verificar que cualquier skill de automatización
invocado desde el grafo de expedientes (extracción de información de PDFs, transformación
de documentos, validación de documentos aportados por el ciudadano) se ejecuta en el
Edge node, no en el cloud.

**Problema que resuelve:** Los expedientes contienen datos personales y documentación
sensible del ciudadano. Si los scripts de procesamiento se ejecutaran en el cloud, los
datos originales cruzarían la frontera del perímetro del cliente, violando el modelo
de privacidad selectiva definido en §7.2 de `Arquitectura.md` y los requisitos del
modo `DEPLOY_MODE=edge`. El ENS (Esquema Nacional de Seguridad) impone restricciones
sobre dónde pueden procesarse documentos de categoría media/alta.

**Aplicación práctica:**
- El nodo del grafo que invoca un skill llama al Thin Client vía WebSocket con un
  script firmado por el Edge.
- El cloud (orquestación LangGraph) recibe el resultado ya procesado: datos extraídos
  o documentos transformados, nunca el documento original.
- Esta regla aplica a: extracción PDF (basada en Docling-edge), validación de formatos
  ENI, generación de índices de documentos, cualquier script del Script Registry
  invocado como acción de una fase del expediente.
- El checklist de cierre de cada Prompt Ei debe incluir una verificación explícita de
  que ningún documento original viaja al cloud.

**Dependencias:** FASE 12.E2 (nodos del grafo de expedientes) · FASE 14 (Sandbox Edge)
· Prompt 9.16 (Thin Client con handlers) · Subfase 2.A completa.

> **Este invariante NO genera un prompt independiente.** Se verifica como criterio de
> aceptación en cada prompt de la Subfase 3.C que implique procesamiento de documentos.

---

## Fase Deploy — Prompt D.6: Edge Node Híbrido (al finalizar Fase 3)

### Prompt D.6 — Edge node: despliegue híbrido cloud/edge en GCP

**Objetivo**: documentar cómo desplegar el modo `DEPLOY_MODE=edge` dentro de la nube privada de un cliente (requisito regulatorio para datos sensibles) mientras el cloud admin (`DEPLOY_MODE=cloud`) permanece en el proyecto GCP central.

**Arquitectura**:

```
GCP central (partner/admin):
  Cloud Run: govgenai-api (DEPLOY_MODE=cloud)
    → Cloud SQL: solo tablas ConfigBase (HubChatbot, HubClient, HubLLMConfig...)
    → Sirve: panel admin, gestión partners, config sync API

GCP cliente (edge):
  Cloud Run: govgenai-api (DEPLOY_MODE=edge)
    → Cloud SQL del cliente: solo tablas OperationalBase (HubDocument, HubInteraction, chunks...)
    → Sirve: widget chat, ingesta, retrieval — datos nunca salen del GCP del cliente

Comunicación:
  cloud → edge: POST /api/v1/edge/config  (push de configuración: chatbot, prompts, LLM keys)
  edge → cloud: POST /api/v1/edge/telemetry (métricas anonimizadas: nº interacciones, latencia)
```

**Variables que cambian en el edge**:

```bash
DEPLOY_MODE=edge
DATABASE_URL=postgresql+asyncpg://...@/govgenai_edge?host=/cloudsql/CLIENT_PROJECT:REGION:INSTANCE
STORAGE_BUCKET=gs://govgenai-edge-CLIENT_NAME
# No hay LANGFUSE en edge por defecto (datos de conversación no salen del cliente)
```

**Proceso de alta de un cliente nuevo**:

1. Partner crea el cliente en el panel admin cloud → genera `edge_api_key` para autenticar la sync.
2. Ops despliega el stack edge en el GCP del cliente (Terraform module, pendiente de crear).
3. Edge llama a `GET /api/v1/edge/config` con su `edge_api_key` → recibe la configuración inicial.
4. A partir de ahí, el edge opera de forma autónoma; la sync es incremental (solo cambios).

**Tests requeridos**:

```python
# should_register_edge_node_with_api_key
# should_push_config_to_edge_and_receive_ack
# should_receive_anonymized_telemetry_from_edge
# should_reject_edge_config_request_without_valid_api_key
# should_not_expose_operational_routes_in_cloud_mode (DEPLOY_MODE=cloud)
# should_not_expose_admin_routes_in_edge_mode (DEPLOY_MODE=edge)
```

**Pendiente** (no implementado, necesita sprint propio):
- Terraform module para provisionar el stack edge en GCP del cliente (Cloud Run + Cloud SQL + GCS + Secret Manager).
- UI de onboarding de cliente en el panel admin: formulario → genera Terraform vars → instrucciones de deploy.
- Protocolo de sync incremental con retry y backoff (actualmente solo hay el endpoint, sin cliente).

---

**Notas transversales a toda la Fase Deploy**:

- `JWT_EXPIRATION_MINUTES` debe volver a `60` en producción. El valor `10080` (7 días) es únicamente para comodidad en desarrollo local.
- El widget en producción usa `data-api-key` (Prompt D.1), nunca `data-token` JWT.
- El `widget.iife.js` se versiona por commit SHA en la CDN. Los partners que embeben el widget deben actualizar la URL cuando haya breaking changes (no usar `@latest` en producción).
- Cloud Run escala a 0 instancias por defecto. El `embedding-service` debe tener `min-instances=1` para evitar cold starts de 90 s que bloquearían el chat.
- Los backups de Cloud SQL se configuran como política de la instancia (retención 7 días), no como paso manual.

---

## FASE 22: Microservicios de computación pesada — Embedding Service y Docling Service

**Tipo**: Diferido — se activa únicamente cuando los criterios de métricas se cumplan en producción.  
**Estado**: ⏳ No iniciar hasta que los criterios de activación se verifiquen en Cloud Run.  
**Prerrequisitos**: Despliegue en Cloud Run operativo (FASE 9C completa, Cloud SQL Auth Proxy, GCS).  
**Corresponde a**: decisión de infraestructura documentada el 2026-04-27 (ver `CLAUDE.md` sección "Servicios de computación pesada").

**Motivación**: BGE-M3 (~1.1 GB) y Docling (CPU-intensivo) corren actualmente in-process dentro del servidor FastAPI. Esto es correcto y suficiente mientras el despliegue sea pequeño, pero en Cloud Run implica cold start de 30-90 s y 3-4 GB de RAM por instancia. La abstracción `EmbeddingService` (protocolo ya existente) hace que la extracción sea un cambio de inyección de dependencia, sin tocar la lógica de negocio.

**Criterios de activación** — no iniciar antes de que se cumplan los tres:
1. Cold start del API supera **15 s** en Cloud Run (visible en métricas Cloud Run / Langfuse).
2. RAM de la instancia FastAPI supera **2 GB** en uso normal (métrica Cloud Run).
3. Se necesita escalar embedding/Docling de forma independiente al API.

**Arquitectura objetivo**:
```
Cloud Run: govgenai-api (FastAPI, ~512 MB)
    ├─ HTTP → Cloud Run: embedding-service  (min-instances=1, BGE-M3 siempre caliente)
    └─ HTTP → Cloud Run: docling-service    (min-instances=0, escala a 0 entre ingestiones)
    ├─ Cloud SQL (vía Auth Proxy)
    └─ GCS (vía StorageService / fsspec)
```

---

### Prompt 22.1 — Microservicio de embeddings (FastAPI standalone)

**Objetivo**: Extraer `LocalEmbeddingService` a un microservicio FastAPI independiente con su propio Dockerfile y `pyproject.toml`. El servidor principal añade `HttpEmbeddingService` y la fábrica `get_embedding_service()` selecciona la implementación por variable de entorno.

**Archivos nuevos**:
- `services/embedding/main.py`
- `services/embedding/Dockerfile`
- `services/embedding/pyproject.toml`

**`services/embedding/main.py`**:
```python
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI()
_model = SentenceTransformer("BAAI/bge-m3")


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    dimensions: int


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vec = _model.encode(req.text, normalize_embeddings=True)
    return EmbedResponse(embedding=vec.tolist(), dimensions=len(vec))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

**Añadir `HttpEmbeddingService`** a `server/app/modules/agents_hub/services/embedding_service.py`:
```python
class HttpEmbeddingService:
    """Delega la generación de embeddings al microservicio externo."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base_url}/embed", json={"text": text})
            resp.raise_for_status()
            return resp.json()["embedding"]
```

**Actualizar `get_embedding_service()`** — selector por env var:
```python
def get_embedding_service() -> EmbeddingService:
    url = os.environ.get("EMBEDDING_SERVICE_URL")
    if url:
        return HttpEmbeddingService(url)
    return _local_embedding_service_singleton()
```

**Tests requeridos**:
```python
# should_call_embed_endpoint_with_correct_payload
# should_return_embedding_as_list_of_floats
# should_raise_on_http_error_from_microservice
# should_use_local_service_when_no_env_var
# should_use_http_service_when_env_var_set
```

---

### Prompt 22.2 — Microservicio Docling (worker de procesamiento de PDFs)

**Objetivo**: Extraer `DoclingProcessor` a un microservicio FastAPI independiente. El servidor principal llama a `POST /process-pdf` (multipart) y recibe el Markdown resultante. Permite escalar el procesamiento de PDFs a cero instancias cuando no hay ingestión activa.

**Archivos nuevos**:
- `services/docling/main.py`
- `services/docling/Dockerfile`
- `services/docling/pyproject.toml`

**`services/docling/main.py`**:
```python
import os
import tempfile
from fastapi import FastAPI, UploadFile
from docling.document_converter import DocumentConverter

app = FastAPI()
_converter = DocumentConverter()


@app.post("/process-pdf")
async def process_pdf(file: UploadFile) -> dict:
    pdf_bytes = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = _converter.convert(tmp_path)
        markdown = result.document.export_to_markdown()
    finally:
        os.unlink(tmp_path)
    return {"markdown": markdown, "pages": result.document.num_pages}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

**Añadir `HttpDoclingProcessor`** a `server/app/modules/agents_hub/ingestion/docling_processor.py`:
```python
class HttpDoclingProcessor:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def process_pdf_bytes(self, pdf_bytes: bytes) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/process-pdf",
                files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
            )
            resp.raise_for_status()
            return resp.json()["markdown"]
```

**Tests requeridos**:
```python
# should_return_markdown_string_from_valid_pdf
# should_raise_on_invalid_pdf_bytes
# should_include_page_count_in_response
# should_use_http_processor_when_env_var_set
# should_fall_back_to_local_when_no_env_var
```

---

### Prompt 22.3 — Integración: docker-compose y variables de entorno

**Objetivo**: Conectar los dos microservicios al stack de desarrollo. Actualizar `docker-compose.yml` con los dos nuevos servicios. El API principal los usa automáticamente si las variables de entorno están definidas.

**Añadir a `docker-compose.yml`**:
```yaml
  embedding-service:
    build:
      context: ./services/embedding
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      start_period: 120s  # tiempo de carga del modelo BGE-M3

  docling-service:
    build:
      context: ./services/docling
    ports:
      - "8002:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      start_period: 60s
```

**Añadir a `server/.env`**:
```bash
EMBEDDING_SERVICE_URL=http://embedding-service:8001
DOCLING_SERVICE_URL=http://docling-service:8002
```

**Tests requeridos**:
```python
# should_use_http_embedding_service_when_url_env_var_set
# should_use_http_docling_processor_when_url_env_var_set
# should_fall_back_to_local_services_when_env_vars_absent
# integration: should_process_pdf_end_to_end_with_http_docling_and_http_embedding
```

---

---

