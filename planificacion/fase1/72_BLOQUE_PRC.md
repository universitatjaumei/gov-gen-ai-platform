## Bloque PRC — El catálogo de procedimientos entra al asistente de normativa (PENDIENTE, planificado el 2026-09-02)

> **Posición**: BLOQUEADO por dos prerrequisitos externos — **las fichas del catálogo validadas
> por los servicios** (la revisión está en curso: propuesta generada, 363 fichas, 206 con
> banderas) y **la consulta de descarga del dataset** que debe habilitar el equipo del catálogo
> (contrato más abajo; la petición textual está en la Qüestió 6 del informe). Se ejecuta **por
> tandas**, a medida que los servicios validan; PRC.0–PRC.3 pueden adelantarse con la primera
> tanda validada. Independiente de Deploy y del resto de bloques pendientes.

**Origen**: valoración de diseño del 2026-09-02 (recogida como Qüestió 6 en
`docs/EVOLUCIO_I_ASPECTES_PENDENTS.md`). El piloto de normativa funciona pero no contesta
procedimiento (servicio que tramita, plazos, silencio, canal), que no está en las normas sino en
el **catálogo de procedimientos** (363 fichas estructuradas de 15 campos: `TITULO`, `ORIGEN`,
`CONTENIDO`, `DESCRIPCION`, `COLECTIVO`, `DOCUMENTACION`, `PLAZOMAXIMO`,
`SILENCIOADMINISTRATIVO`, `NORMATIVA`, `URLNORMATIVA`, `RESOLUCION`, `URL_TRAMITACION_DEFINIDA`,
`MATERIA1`…; proyecto de revisión en `Descarregar_pdf/normativa_propia/cataleg_procediments/`).

**Decisión de diseño (tomada, con las razones en la Qüestió 6 del informe)**: **un solo
asistente, no dos chatbots con router**. Los usuarios preguntan normativa y procedimiento
mezclados y a menudo no los distinguen; un router clasificaría justo donde el usuario es ambiguo
y sus errores serían pérdida de calidad silenciosa; la mejor respuesta a una pregunta mixta
necesita la ficha y los artículos en el mismo contexto; y los perfiles router/aggregator siguen
sin implementar (hallazgo I5) mientras que la vía de metadatos ya existe.

**Reglas duras del bloque PRC**:

- **Solo entran fichas validadas.** El estado de la ficha en el catálogo es la puerta; un
  borrador o una edición pendiente de valorar no toca el corpus. 28 fichas citan hoy normas
  derogadas: ingerir sin validar es enseñar al asistente a repetirlas con seguridad.
- **El rendido ficha→`.md` es determinista** (plantilla sobre los 15 campos, sin LLM), conforme
  a `docs/CONTRATO_MD_CORPUS.md`, y vive con el proyecto del catálogo — fuera del servidor,
  como el resto del pipeline de curación. Produce paquetes de ingesta con la misma forma que
  los de normativa (`generat/ingesta/`).
- **Las reglas del corpus no se relajan**: la taxonomía (materia, tipo, servicio) va en
  metadatos y NUNCA en `embedding_text`; reclasificar sigue costando un UPDATE. La lengua de
  trabajo es valenciano y el castellano se genera tras la validación, **emparejado por ID de
  ficha** (aquí no hace falta la huella de cifras).
- **La autoridad se distingue en la respuesta, no en el enrutado**: una ficha se cita con
  servicio responsable y fecha de actualización, nunca como si fuera una norma con vigencia.
- **Ninguna cifra de calidad se reporta sin medirla**: el cierre exige el lote dorado
  antes/después.

**Contrato del dataset del catálogo (la petición externa, decidida el 2026-09-02)**: la
sincronización es **por estado completo, no por deltas de tiempo**. Un filtro «actualizados en
las últimas N horas» no puede expresar bajas, obliga a llevar contabilidad de la última pasada
exitosa (una ventana perdida = divergencia permanente y silenciosa) y depende de fechas que
mienten barato; el estado completo con comparación por hash en destino no tiene ninguno de los
tres problemas, y a 363 fichas (~2 MB) descargarlo entero cuesta menos que diseñar el delta.
El endpoint que se pide al equipo del catálogo:

1. **HTTPS autenticado** (token de servicio), consulta **pull** — la plataforma llama con su
   cadencia; el catálogo no sabe que el chatbot existe.
2. **Solo fichas validadas**: expone el estado *publicado*, nunca borradores ni ediciones
   pendientes.
3. **Completitud declarada**: `generated_at` + `total`, y el consumidor verifica que recibió
   `total` filas (la lección de `is_census()`: una respuesta truncada no puede pasar por censo).
4. **Por ficha**: ID **estable**, lengua, los 15 campos, `data_actualitzacio`; hash de contenido
   opcional (sin él, el hash se calcula en destino sobre el rendido determinista).
5. **Bajas explícitas si puede ser** (estado `retirada` + fecha); si no, la ausencia del censo
   funciona como baja, protegida por la salvaguarda de proporción.
6. **Sin filtro por fechas ni por cambios**: el incremento lo da la huella en destino.

---

### Prompt PRC.0 (RED/GREEN) — El cliente del dataset y la validación del contrato

**Modelo sugerido**: **Sonnet** — cliente HTTP con contrato cerrado arriba.

**Objetivo**: descargar el estado completo del catálogo, validar el contrato y dejar el export
que PRC.1 consume. Vive con el proyecto del catálogo (fuera del servidor), como el resto del
pipeline.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.0 (RED/GREEN) — cliente del dataset del catálogo (en cataleg_procediments/)

- Cliente HTTP con token por variable de entorno; sin credenciales en código ni en el repo.
- Validación del contrato ANTES de escribir nada: generated_at presente, len(filas) == total,
  ID estable y campos mínimos por ficha. Censo incompleto o malformado -> se aborta CON el
  motivo y no se toca el export anterior (la pasada anterior sigue siendo la buena).
- Salida: el export normalizado (la forma de fitxes_cataleg_complet.json) del que parte
  PRC.1, con las retiradas marcadas si el endpoint las da explícitas.
- Registro de cada descarga: generated_at, total, cuántas validadas, cuántas retiradas —
  una línea por pasada, para poder auditar cuándo divergieron los sistemas.
- Tests: respuesta truncada (len < total) rechazada sin escribir; total=0 rechazado con
  mensaje distinto (un catálogo vacío no es creíble, es un error del origen); retirada
  explícita llega al export; token ausente -> error claro; idempotencia (misma respuesta ->
  mismo export byte a byte).
```

**Verificación**: una descarga real contra el endpoint (o contra un doble local con la misma
forma mientras el equipo del catálogo lo habilita) con su línea de registro.

---

### Prompt PRC.1 (RED/GREEN) — El rendido determinista ficha→`.md` y el paquete de ingesta

**Modelo sugerido**: **Sonnet** — transformación mecánica con contrato ya escrito.

**Objetivo**: script en el proyecto del catálogo que rinde cada ficha **validada** a un `.md`
conforme al contrato del corpus, listo para los cargadores existentes.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.1 (RED/GREEN) — rendido ficha -> .md (vive en cataleg_procediments/, no en server/)

- Entrada: el export normalizado que deja PRC.0 (con fallback a un fichero local con la
  misma forma, para desarrollo y para la primera tanda si el endpoint aún no existe).
  Salida: un .md por ficha y lengua conforme a docs/CONTRATO_MD_CORPUS.md.
- Estructura del .md: título = nombre del procedimiento; secciones con encabezados (què és,
  qui pot demanar-ho, documentació, terminis i silenci, on es tramita, normativa aplicable).
  El embedding_text resultante solo lleva contexto estructural, como siempre.
- Frontmatter: tipus_document=procediment, servei (ORIGEN), materia mapeada al vocabulario
  vigente, col.lectiu, data_actualitzacio, validada_per, url_tramitacio, url_fitxa (fuente
  canónica para la cita), id_ficha para el emparejamiento bilingüe.
- Determinista e idempotente: mismo export -> mismos bytes (el hash del reconciliador decide
  qué reingiere). Ficha sin los campos mínimos (título, servicio, contenido) -> se excluye
  CON AVISO en el resumen, nunca en silencio.
- Tests (en el proyecto del catálogo, como los scripts existentes): round-trip de una ficha
  completa; exclusión avisada de una incompleta; idempotencia byte a byte; el frontmatter
  valida contra el contrato del corpus.
```

**Verificación**: paquete generado con la primera tanda real (o una muestra validada a mano) y
`load.py --dry-run` sobre él sin errores de contrato.

---

### Prompt PRC.2 (RED/GREEN) — El eje «tipo de documento» en el corpus

**Modelo sugerido**: **Opus** — toca los invariantes del corpus (ejes, filtro, índice agéntico).

**Objetivo**: que el corpus distinga `norma` de `procediment` como **eje** (estructura, StrEnum:
pocos y estables), consumido por el filtro de metadatos y por el índice del modo agéntico.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.2 (RED/GREEN) — eje tipus_document. Deploy: edge

- StrEnum TipusDocument {norma, procediment} donde viven los ejes del corpus; las normas
  existentes son norma por defecto (migración de datos con recuento antes/después).
- El frontmatter del contrato admite tipus_document; el cargador lo persiste en metadatos.
- MetadataFilter gana el eje (vacío = sin restringir, como ambits/submateries).
- El índice del modo agéntico (nivel 0 y listado) presenta las fichas de procedimiento como
  documentos propios, distinguibles de las normas.
- Las fichas NO entran en la lógica de vigencia normativa: su frescura es
  data_actualitzacio, no estat_vigencia (test que fija que la vigencia no se les aplica).
- Tests: filtro por eje en las dos direcciones; migración deja todo lo existente en norma;
  taxonomía sigue sin entrar en embedding_text (el test existente lo cubre, verificar que
  cubre también las fichas).
```

**Verificación**: suite de ingesta + retrieval + higiene verdes; migración aplicada.

---

### Prompt PRC.3 (RED/GREEN) — La autoridad de la ficha en la respuesta

**Modelo sugerido**: **Sonnet** — mismo mecanismo que el marcador de vigencia, ya existente.

**Objetivo**: que el asistente cite una ficha como lo que es — «segons la fitxa del catàleg
(Servei X, actualitzada el …)» con su `url_fitxa` — y nunca como norma.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.3 (RED/GREEN) — marcador de autoridad por documento

- En el bloque de fuentes del prompt, un documento tipus_document=procediment lleva su marca
  con servicio y fecha (el patrón de VIGENCIA NO VALIDADA: marcado por documento, no aviso
  general), y la instrucción de verbalizarla al citarlo.
- La cita de una ficha usa url_fitxa como URL canónica (el validador de citas la acepta).
- Preparado para la caducidad: si la ficha supera el umbral de revalidación (parámetro, sin
  activar por defecto), la marca añade «pendent de revisió» — la decisión de activarlo es de
  los servicios (decisión 16 del informe).
- Tests: el prompt final contiene la marca para una ficha y no para una norma; la respuesta
  que cita una ficha pasa el contrato de citas con url_fitxa; el umbral apagado no marca.
```

**Verificación**: conversación real con una pregunta de procedimiento; la respuesta cita la
ficha con servicio y fecha.

---

### Prompt PRC.4 (RED/GREEN) — La sincronización con el catálogo, supervisada y luego programada

**Modelo sugerido**: **Sonnet** — reutiliza reconciliador, poda y salvaguarda existentes.

**Objetivo**: el circuito de actualización completo: el formulario edita, el catálogo publica
(solo validadas), el corpus sincroniza por hash.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.4 (RED/GREEN) — sync del catálogo de procedimientos. Deploy: edge

- Fuente: el paquete que produce PRC.1 (directorio local o el sistema de publicación, la
  misma dualidad load/sync del corpus normativo). El reconciliador existente hace deltas,
  poda y salvaguarda de proporción — no se duplica nada.
- Alta/cambio: solo lo que cambió de hash se reingiere. Baja: ficha retirada del catálogo ->
  poda, protegida por la salvaguarda de proporción.
- Bilingüe: val + es emparejadas por id_ficha (metadato del frontmatter de PRC.1).
- Cadencia: las primeras pasadas MANUALES y supervisadas (la decisión de SYNC.1: no se
  programa a ciegas); tras dos pasadas limpias documentadas, entrada en el scheduler con
  cadencia diaria + comando manual para la corrección urgente. El informe de cada pasada
  queda registrado (qué entró, qué se reingirió, qué se podó).
- Tests: cambio de una ficha reingiere solo esa; export roto (censo parcial) no poda gracias
  a la salvaguarda; la validación es puerta (una ficha no validada en el export no entra).
```

**Verificación**: una pasada real supervisada con su informe; editar una ficha de prueba y ver
que solo ella se reingiere.

---

### Prompt PRC.5 — Recalibración medida y cierre

**Modelo sugerido**: **Opus** — calibración y lectura de medidas, donde una cifra artefacto
cuesta cara.

**Objetivo**: medir el efecto de las fichas en la recuperación y cerrar con evidencia.

**Instrucciones al agente**:
```markdown
# PROMPT PRC.5 — antes/después con el lote dorado + preguntas mixtas

- Lote dorado (medir_lote.py) ANTES de ingerir la tanda y DESPUÉS: las consultas de
  normativa no deben degradarse (si el umbral 0,65 deja de ser el punto bueno, recalibrar
  con la curva, no a ojo).
- Añadir al lote escenarios NUEVOS de procedimiento y mixtos (norma+trámite), anotados con
  su fuente esperada (ficha, norma, o ambas). La pregunta mixta es el caso que justificó la
  integración: hay que medirla, no suponerla.
- Verificación en navegador de tres conversaciones reales: pura normativa, puro
  procedimiento, mixta — con las citas correctas en cada una.
- Cierre: cifras reales en el informe del bloque, docs/CATALEG_PROCEDIMENTS_CORPUS.md con el
  circuito (rendido, puerta de validación, sync, caducidad) y las decisiones 14-16 del
  informe con lo que se haya decidido.
```

**Al cerrar el bloque**: suite completa desde Git Bash; el `.bat` humano solo si algo quedó
fuera del alcance del navegador (previsiblemente nada).
