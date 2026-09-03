## Bloque EXT — Frontera de la extracción: qué entra al corpus y qué es contexto (PENDIENTE, va ANTES de Deploy)

> **Contexto**: `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` (2026-08-10). «Subir un documento»
> significaba lo mismo para dos cosas distintas y se separan: el **corpus** —lo que el
> asistente cita ante un ciudadano— solo entra como `.md` conforme a `CONTRATO_MD_CORPUS.md`;
> el **contexto temporal** —un documento que alguien aporta para preguntarle cosas, o una
> entrada de un informe— se extrae con pdfplumber.
>
> La asimetría tiene razón: en el contexto la persona tiene el documento delante y ve si la
> extracción salió mal; en el corpus, una extracción mala es una **cita errónea** que no
> detecta nadie y que sale con la autoridad de una norma.
>
> **Va antes de Deploy** porque retira Docling, y la huella que quede es la que dimensiona la
> VM en D.4.

---

### Prompt EXT.1 (RED/GREEN) — Al corpus solo entra `.md` conforme al contrato

**Modelo sugerido**: **Sonnet** — retirada acotada con verificación por grep; el contrato del
`.md` ya existe y el cargador ya lo consume.

**Objetivo**: `hub_ingestion_router` acepta hoy PDF y lo convierte con Docling dentro de la
petición. Eso produce documentos sin front-matter, sin anclas de artículo y sin estado de
vigencia — es decir, contenido que el asistente **no puede citar** como norma, entrando por la
misma puerta que el corpus curado.

```
# PROMPT EXT.1 (RED/GREEN) — El corpus se alimenta del pipeline, no del navegador
# Deploy: edge

## Cambios
- hub_ingestion_router: la subida al corpus acepta SOLO .md/.markdown (UploadKind.TEXT, que ya
  existe desde SEC.6). Un PDF se rechaza con 415 y un mensaje que diga a dónde ir: el
  documento se convierte en el pipeline de curación, no aquí.
- Validar el front-matter en la subida con `entry_from_frontmatter` (el mismo que usa
  `corpus.load`), para que un .md sin los campos del contrato se rechace en el momento y no
  aparezca a medias en el corpus. Reportar TODOS los campos que faltan, no el primero.
- watcher.py: la ruta de conversión con Docling del corpus deja de usarse (la retirada del
  paquete es EXT.3, aquí solo se deja de llamar).
- frontend DocumentsPage/UploadDropzone: el formato aceptado y el mensaje de error reflejan
  la regla. i18n en es/ca/en, sin cadenas sueltas.

## FUERA DE ALCANCE
- `api/v1/ingestion.py::user_upload` (contexto temporal del usuario) — es EXT.2.
- Los pipelines de redacción — son EXT.2.

## Tests (RED primero)
# should_reject_a_pdf_upload_to_the_corpus_with_415
# should_accept_a_markdown_that_conforms_to_the_contract
# should_reject_a_markdown_without_frontmatter_listing_every_missing_field
# should_not_call_docling_from_the_corpus_path

## Cierre
- [ ] `grep -rn "docling" server/app/modules/agents_hub/ingestion/watcher.py` = 0
- [ ] La pantalla de documentos dice qué formato acepta y por qué (i18n es/ca/en)
```

---

### Prompt EXT.2 (RED/GREEN) — El contexto temporal se extrae con pdfplumber, y un escaneado falla en alto

**Modelo sugerido**: **Sonnet** — sustitución de una librería por otra con contrato de salida
conocido; la guarda de documento vacío es la única decisión, y está cerrada en el prompt.

**Objetivo**: las dos vías de contexto —el PDF que sube una persona para preguntarle cosas y
el PDF que entra como fuente de un informe de redacción— usan Docling. `pdfplumber` **ya es
dependencia directa** (`server/pyproject.toml:44`), así que el cambio no añade nada y quita
los modelos de layout y RapidOCR.

```
# PROMPT EXT.2 (RED/GREEN) — pdfplumber en las dos vías de contexto
# Deploy: edge

## Cambios
- api/v1/ingestion.py::user_upload → extracción con pdfplumber en vez de IngestionWatcher/Docling.
- modules/redaccion/pipelines/pdf_text_pipeline.py → pdfplumber. Ya usaba Docling SIN OCR, así
  que el contrato de salida no cambia: texto de PDFs con capa de texto.
- Extractor compartido y no dos copias: el troceado y el aviso de documento vacío son los
  mismos para las dos vías.

## La guarda que hace aceptable perder OCR
- Sin capa de texto, pdfplumber devuelve poco o nada. Ingerir eso en silencio produce un
  documento VACÍO que no ve nadie — la avería muda que esta auditoría ya encontró tres veces.
- Umbral por página (no absoluto: un PDF de 80 páginas con 200 caracteres está tan vacío como
  uno de 1 con 0). Por debajo → 422 con un mensaje que diga que el documento parece escaneado
  y que hace falta pasarlo por el pipeline de curación, que sí tiene OCR.
- El mensaje es para una persona, no para un log: nada de "extraction failed".

## Tests (RED primero)
# should_extract_text_from_a_digital_pdf
# should_reject_a_scanned_pdf_with_an_explicit_message
# should_use_a_per_page_threshold_not_an_absolute_one
# should_share_the_extractor_between_user_upload_and_redaccion
# should_preserve_the_redaccion_pipeline_output_contract   (regresión: mismo contrato que Docling sin OCR)

## Cierre
- [ ] Los tests de redacción que cubrían el pipeline de PDF siguen verdes sin cambiar sus aserciones
- [ ] `origen_del_text` sigue siendo el único sitio donde se declara que un texto viene de OCR
```

---

### Prompt EXT.3 — Retirada de Docling y medición de la huella

**Modelo sugerido**: **Sonnet** — retirada mecánica + medición. La cifra que salga es la que
dimensiona la VM en D.4, así que se mide, no se estima.

```
# PROMPT EXT.3 — Fuera del árbol, y cuánto ocupa lo que queda
# Deploy: n/a

## Retirada (Caso B: borrado directo, no hay migración en curso)
- Borrar `modules/agents_hub/ingestion/docling_processor.py` y sus llamantes muertos.
- Quitar `docling` de `server/pyproject.toml` y regenerar el lock.
- Barrido: `grep -rn "docling\|Docling\|rapidocr" server/` = 0 fuera de comentarios históricos.
- Ojo a `test_data_anonymizer.py` y `pipelines/{contracts,factory}.py`, que también lo nombran.

## Medición (el dato que necesita D.4)
- Arrancar la aplicación con el compose de producción y medir, SIN Docling:
    - memoria residente en reposo y durante una subida de contexto,
    - tiempo de arranque hasta el primer 200,
    - tamaño de la imagen.
- Repetir con una ingesta de corpus real (`corpus.load` sobre md_contracte) para ver el pico.
- Anotar las cifras en `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §Dimensionado, que hoy dice
  explícitamente que están sin medir.

## Cierre
- [ ] Suite backend completa en verde tras la retirada
- [ ] La imagen construye sin docling y arranca
- [ ] Las cifras están escritas, con el método con que se midieron
```

---
