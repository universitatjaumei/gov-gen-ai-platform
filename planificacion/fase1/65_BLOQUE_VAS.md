## Bloque VAS — Verificaciones como servicio: citas, vigencia y auditoría estática por API (PENDIENTE, planificado el 2026-09-02)

> **Posición**: **después del Bloque REG**, del que consume el patrón de scopes de PAT (REG.2), el
> evento de actividad (REG.1) y el transporte MCP remoto (REG.4). Independiente de FUN, PLG, DIN y
> PRC. 4 prompts cortos. Todo es **`Deploy: edge`**.

**Origen**: `docs/GOVERNANCA_PER_API.md` §4 (2026-09-02), preparado para contestar la posición de
desarrollo («gobernanza y experimentación sí; desarrollar es cosa nuestra»). La respuesta es que
**definidos los parámetros de gobernanza de un caso de uso, la UADTI desarrolla fuera con registro
por API dentro**, y para que eso sea literal faltan servicios que hoy existen como función interna.
De los seis candidatos del documento, este bloque toma los **tres de coste bajo que ya existen como
código y solo necesitan una superficie**: el contrato de citas, el estado de vigencia de un
documento y la auditoría estática. Los otros tres (parámetros de gobernanza por caso de uso,
depósito de manifiestos, asistentes externos con escenarios) siguen sin planificar y esperan a la
primera aplicación externa real.

**Por qué estos tres y no otros**: ninguno toca el modelo, ninguno depende del corpus de la
plataforma para funcionar (la vigencia lo consulta, no lo requiere), y los tres son
**deterministas**: la misma entrada da la misma salida, así que exponerlos no crea una segunda
fuente de verdad ni una deriva posible. La auditoría estática es además **la revisión posterior
del nivel 2 de la Instrucció 02/2026 para código que no corre en la plataforma**, y el candidato
que mejor encaja con el papel que la Instrucció da a la UADTI (§8.4 y §9).

**Reglas duras del bloque VAS**:

- **Sin segunda implementación.** Cada servicio envuelve la función que ya usa el motor
  (`enforce_citation_contract`, `marca_de_vigencia`/`aviso_para`, `ScriptSecurityAuditor.audit`).
  Si el servicio necesita algo que la función no da, se cambia la función y el motor lo hereda;
  nunca una copia «para la API». Un test por servicio comprueba que el veredicto de la API y el
  del motor coinciden sobre los mismos casos.
- **El texto no se guarda.** Ni la respuesta que se verifica, ni el código que se audita, tocan
  logs ni base de datos: la misma regla que REG.3 para la anonimización, con test. Lo que se
  registra es el veredicto y, si hace falta evidencia, un `payload_hash`.
- **Un scope, `verificaciones:use`**, emisible por superadmin y admin (los tres servicios son de
  lectura o de cómputo sin efecto; el riesgo dominante es el volumen, y lo acota la cuota).
- **La auditoría registra un evento REG; las otras dos no.** Auditar un script es un acto de
  gobernanza (la revisión posterior de la Instrucció) y deja rastro: quién auditó qué hash, con qué
  nivel de riesgo, cuándo. Verificar citas o consultar vigencia son comprobaciones sin estado: la
  aplicación externa registra **su** actividad por REG.2, y un evento por cada comprobación
  duplicaría el registro sin decir nada nuevo. Escrito en el contrato para que nadie lo «arregle».
- **La vigencia respeta la tenencia y el filtro cerrado.** Solo documentos de chatbots visibles
  para la organización del PAT y que pasen `MetadataFilter()` por defecto (público, no superseded,
  apto para asistentes). Preguntar por un documento que no se puede recuperar devuelve 404, no
  «no validado»: el título ya dice que existe.
- **Las reglas del auditor se publican desde el código.** El endpoint que lista la caja de
  herramientas lee los `frozenset` del auditor; no hay una lista paralela en un `.md` ni en un
  JSON. Es lo que permite pedirle a la UADTI que las contraste con las Guías Operativas Técnicas
  sin que el documento y el sistema puedan divergir.

---

### Prompt VAS.1 (RED/GREEN) — El scope y el contrato de citas como servicio

**Modelo sugerido**: **Sonnet** — envolver una función existente en un router con el patrón de
scopes de REG.2.

**Objetivo**: que una aplicación externa aplique la misma regla de «ninguna afirmación sin fuente
resoluble» que el motor, sobre una respuesta generada fuera.

**Instrucciones al agente**:
```markdown
# PROMPT VAS.1 (RED/GREEN) — verificaciones:use + POST /api/v1/verificaciones/citas. Deploy: edge

## Scope
- `verificaciones:use` en el catálogo de scopes (core/auth/pat/scopes.py), emisible por
  superadmin y admin. Documentado en docs/MCP_SERVER.md §3 (mapa scopes → tools) aunque el
  tool MCP llegue en VAS.4.

## Router (server/app/routers/verificaciones_router.py, prefix /verificaciones, Deploy: edge,
## registrado en _register_edge)
- POST /api/v1/verificaciones/citas
  Entrada: {texto: str, fuentes_permitidas: [{url, titulo?}], modo: "RAG"|"MD_LONG_CONTEXT"|
  "MD_AGENT_SELECTOR" (default RAG), mensaje_sin_respuesta?: str}.
  Salida: {cumple: bool, texto_resultante: str, citas_validas: [url], citas_invalidas: [url],
  remisiones_despojadas: int, anclas_degradadas: int}.
  Implementación: enforce_citation_contract(...) y has_valid_citations(...) tal cual; el
  desglose (válidas/inválidas/degradadas/despojadas) se obtiene de las funciones que ya
  componen el contrato (degradar_anclas, despojar_remisiones), sin reimplementar el regex.
- Límite de tamaño de `texto` (misma constante que el límite de entrada del sandbox de FUN.6 si
  ya existe; si no, 64 KB) -> 413.
- Cuota: cuenta como interacción del PAT en la cuota de organización/mes (SEC.4); no se
  inventa una cuota nueva.
- Ni `texto` ni `fuentes_permitidas` se registran en logs ni en BD (test con captura de logs y
  espía sobre la sesión).

## Tests (mínimo 6) — server/tests/routers/test_vas1_citas.py
- Sin scope -> 403; con `verificaciones:use` -> 200.
- Texto con cita a una URL permitida -> cumple=True y aparece en citas_validas.
- Texto sin ninguna cita válida -> cumple=False y texto_resultante == mensaje_sin_respuesta
  (el de la petición o NO_CITATION_FALLBACK).
- Cita a URL no permitida -> en citas_invalidas; el texto resultante la trata igual que el
  motor (test de paridad: mismo caso por la API y por CoreGraph -> mismo texto).
- Texto > límite -> 413.
- El texto no aparece en logs ni en ninguna escritura de BD.
```

**Verificación**: suite del directorio + higiene verdes; `curl` real con un PAT de prueba y un texto
con una cita válida y otra inválida; el contrato en OpenAPI regenerado.

---

### Prompt VAS.2 (RED/GREEN) — El estado de vigencia de un documento del corpus

**Modelo sugerido**: **Sonnet** — lectura acotada por tenencia sobre datos que ya existen.

**Objetivo**: que una aplicación externa que cite normativa del mismo corpus no afirme como vigente
lo que la plataforma avisaría.

**Instrucciones al agente**:
```markdown
# PROMPT VAS.2 (RED/GREEN) — GET /api/v1/verificaciones/vigencia. Deploy: edge

## Endpoint
- GET /api/v1/verificaciones/vigencia?document_id=<uuid> | ?url=<url canónica>
  (exactamente uno de los dos; ambos o ninguno -> 422).
  Salida: {document_id, titulo, url, estat_vigencia, vigencia_validada: bool,
  vigencia_validada_el: datetime|null, vigencia_validada_por: str|null,
  necesita_aviso: bool, aviso: str|null, superseded_por: {document_id, url}|null,
  lengua, version_pareja: {document_id, url, lengua}|null}.
  `necesita_aviso` y `aviso` salen de marca_de_vigencia(documento) y del mismo texto que
  añade el CoreGraph (aviso_para sobre un item sintético del documento), no de una copia.
- Tenencia: el documento pertenece a un chatbot visible para la organización del PAT
  (scope_query_to_orgs sobre hub_chatbots -> hub_documents) Y pasa MetadataFilter() por
  defecto. Si no -> 404 (no 403: no revelar existencia).
- La URL se normaliza con la misma función que usa el emparejador de citas (barra final,
  http/https, ancla) — está en evaluation/escenario_metricas.py; reutilizarla, no copiarla.
- Sin evento REG (regla del bloque). Cuota como en VAS.1.

## Tests (mínimo 6) — server/tests/routers/test_vas2_vigencia.py
- Documento validado -> necesita_aviso=False, aviso=None.
- Documento con estat 'vigent?' sin validar -> necesita_aviso=True y el aviso es
  byte a byte el que añadiría el CoreGraph (test de paridad).
- Documento superseded -> 404 (el filtro cerrado lo excluye) aunque exista.
- Documento de una organización ajena -> 404.
- url con barra final / sin esquema -> resuelve al mismo documento.
- document_id y url a la vez -> 422; ninguno -> 422.
```

**Verificación**: suite + higiene verdes; `curl` real sobre un documento del corpus de Normativa
con `vigent?` y otro validado; OpenAPI regenerado.

---

### Prompt VAS.3 (RED/GREEN) — La auditoría estática como servicio, con evento REG y la caja de herramientas publicada

**Modelo sugerido**: **Sonnet** — la función existe con tres niveles y línea por hallazgo; el
trabajo es el router, el evento y la lista publicada desde el código.

**Objetivo**: la revisión posterior del nivel 2 de la Instrucció para código que no corre en la
plataforma, con la misma vara que el catálogo de funciones, y la caja de herramientas consultable.

**Instrucciones al agente**:
```markdown
# PROMPT VAS.3 (RED/GREEN) — POST /api/v1/verificaciones/codigo + GET .../codigo/reglas. Deploy: edge

## Auditar
- POST /api/v1/verificaciones/codigo {codigo: str, finalidad?: str}
  Salida: AuditResult tal cual lo produce ScriptSecurityAuditor.audit (nivel SAFE|WARNING|
  CRITICAL, hallazgos con regla, detalle y línea, puede_revisarse, approved) más
  code_sha256. No se añade ni se quita nada al veredicto: la API y el catálogo de funciones
  miran el mismo objeto (test de paridad con el auditor invocado directamente).
- El código NO se guarda ni se registra: solo code_sha256 (test con captura de logs y espía
  sobre la sesión).
- Evento REG (ActividadIAEvent): actor = dueño del PAT, herramienta = cliente del PAT,
  finalidad = la del cuerpo o «auditoría de código», payload_hash = code_sha256, y en los
  metadatos permitidos por el contrato el nivel de riesgo. Si el contrato de REG.1 no admite el
  nivel de riesgo como metadato, se añade a REG.1 la clave (es un campo de gobernanza, no de
  contenido) y se documenta.
- Límite de tamaño del código (el mismo del sandbox) -> 413. Cuota como en VAS.1.

## La caja de herramientas
- GET /api/v1/verificaciones/codigo/reglas (mismo scope):
  {modulos_permitidos: [...], capacidades_denegadas: [...], reglas: [{id, nivel, descripcion}],
  version_auditor: str}. Se construye leyendo los frozenset y las reglas del propio
  ScriptSecurityAuditor; `version_auditor` es un hash estable de ese contenido, para que un
  cliente sepa si la caja de herramientas cambió desde la última vez.
- Test de que la respuesta se deriva del auditor: cambiar el frozenset en un monkeypatch
  cambia la respuesta (no hay lista paralela).

## Tests (mínimo 7) — server/tests/routers/test_vas3_codigo.py
- Sin scope -> 403.
- Script limpio -> SAFE, puede_revisarse=True, approved=True.
- Script con import fuera de la lista -> WARNING con línea; con eval() -> CRITICAL.
- Paridad: el mismo script por la API y por el auditor directo -> mismo AuditResult.
- El código no aparece en logs ni en BD; el evento REG lleva code_sha256 y no el código.
- El evento REG se escribe con el nivel de riesgo.
- /reglas se deriva del auditor (monkeypatch) y version_auditor cambia si cambia el contenido.
```

**Verificación**: suite + higiene verdes; `curl` real con un script con `eval` y otro limpio; el
evento visible en la lectura del registro (REG.5); OpenAPI regenerado.

---

### Prompt VAS.4 — Los tres servicios en el MCP remoto, y la documentación

**Modelo sugerido**: **Sonnet**.

**Objetivo**: que un agente los use como tools, y que `docs/GOVERNANCA_PER_API.md` deje de
llamarlos candidatos.

**Instrucciones al agente**:
```markdown
# PROMPT VAS.4 — tools MCP + documentación

## MCP (mcp_server/, mismo paquete y transporte remoto de REG.4; sigue sin importar server/app)
- Tools verificar_citas, consultar_vigencia, auditar_codigo, clientes HTTP finos sobre los
  tres endpoints, con el token de cada cliente propagado por petición (patrón REG.4).
  Mapa scope -> tool en docs/MCP_SERVER.md §3 y §6.

## Documentación
- docs/GOVERNANCA_PER_API.md: las tres filas pasan de «Candidat» a «Hui (VAS.n)»; §4.4, §4.5 y
  §4.6 se reescriben como «fet» con el contrato de cada endpoint; §4 intro dice que quedan
  tres candidatos.
- docs/MCP_SERVER.md: ejemplo de sesión «auditar un script antes de compartirlo en el
  servicio» (el caso de la Instrucció).
- docs/CATALOGO_FUNCIONES.md (si FUN ya cerró) o nota en FUN.7: la sección «La caja de
  herramientas» enlaza al endpoint /reglas como fuente, en vez de listar las reglas.

## Verificación
- Sesión MCP real contra el servidor con las tres tools; evidencias en el informe de cierre.
```

**Al cerrar el bloque**: suite completa desde Git Bash; sin `.bat` humano (todo es API y se verifica
con `curl` y una sesión MCP).

---
