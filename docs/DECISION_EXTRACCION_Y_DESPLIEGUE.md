# Decisión — frontera de la extracción y forma del despliegue

> **Fecha**: 2026-08-10. **Estado**: aceptada y aplicada — Docling se retiró en EXT.3 y el
> despliegue es VM, no Cloud Run. **Sustituye** a la sección de servicios de computación pesada
> de `AGENTS.md`, que pedía extraer Docling y BGE-M3 a servicios separados de Cloud Run.
> **Origen**: conversación de arquitectura tras `docs/AUDITORIA_PRE_DEPLOY.md`
> y el cierre del bloque SEC.8. **Afecta a**: bloque EXT (nuevo) y bloque Deploy (reescrito).

Dos decisiones que se tomaron juntas porque la segunda depende de la primera: qué extrae
documentos dentro de la aplicación determina cuánta máquina hace falta.

---

## 1. Dos vías de documento, y solo una entra al corpus

Hasta ahora «subir un documento» significaba lo mismo para dos cosas muy distintas. Se
separan:

| Vía | Qué es | Cómo entra |
|---|---|---|
| **Corpus normativo** | Lo que el asistente **cita** ante un ciudadano | Solo `.md` conforme a `CONTRATO_MD_CORPUS.md` |
| **Contexto temporal** | Un documento que alguien aporta para preguntarle cosas, o una entrada de un informe de redacción | PDF/ofimática, extraído con **pdfplumber** |

**Por qué la asimetría.** En el contexto temporal la persona tiene el documento delante: si
la extracción sale regular, lo ve en la respuesta y reformula. En el corpus, una extracción
mala se convierte en una **cita errónea** que no detecta nadie, y que sale con la autoridad
de una norma. Por eso el corpus tiene un contrato: el `.md` es un artefacto **revisado**, con
front-matter, anclas de artículo y estado de vigencia; nada de eso lo produce una conversión
automática dentro de una petición web.

### Consecuencia: la conversión sale de la aplicación

El pipeline que convierte el documento original a `.md` **vive fuera** y seguirá fuera. Hoy es
el proyecto de curación (`Descarregar_pdf/normativa_propia/`, con sus scripts y su OCR
propio); mañana lo más probable es que se pida a los servicios proponentes un documento con
una **plantilla de estructura conocida** y se convierta con **pandoc**.

Eso es más sólido que convertir PDF maquetado: pandoc es determinista, no necesita modelos, y
sobre todo **mueve el problema al origen** —si la fuente trae estructura, no hay que
adivinarla—. Es el mismo principio que el contrato ya aplica al BOE y al DOGV: «no se escribe
el `.md` a mano, se genera desde el XML consolidado».

Mientras el pipeline definitivo no esté cerrado, puede vivir en local o en un cuaderno; es
exploración, y el corpus normativo es público. **Dos límites**: la *carga* al RAG
(`corpus.load`) no se ejecuta desde un cuaderno —necesita la base, las credenciales de
embedding y la guarda de procedencia—, y cuando esto llegue a **expedientes** (fase 3) la
conversión tampoco puede salir a un runtime de terceros, porque ahí hay datos personales.

### Qué se pierde: OCR. Y por qué no es una pérdida

Sin Docling no hay OCR en el servidor. Pero el OCR **ya está fuera**: la curación tiene el
suyo (`ocr_windows.ps1`, `recupera_ocr_perdut.py`) y el contrato tiene un campo,
`origen_del_text`, precisamente para marcar los documentos que vienen de una transcripción
automática que nadie ha podido verificar contra un original digital. Es decir, el OCR está
donde puede revisarse, que es donde debe estar — y no en una petición web.

**Condición innegociable del cambio**: un PDF escaneado tiene que **fallar en alto**. Sin capa
de texto, pdfplumber devuelve poco o nada; ingerir eso en silencio produce un documento vacío
que nadie ve. La subida debe rechazarlo diciendo que el documento parece escaneado.

---

## 2. El despliegue es una VM, no Cloud Run

**Decisión**: la aplicación corre en una **VM** de GCP con Docker Compose; el **estado sigue
gestionado** (Cloud SQL para Postgres, GCS para documentos).

### Por qué

1. **Hay procesos que necesitan un proceso vivo.** El planificador de calidad de contenido es
   un APScheduler dentro del `lifespan`, y el rastreo de curación se encola con
   `BackgroundTasks`. En Cloud Run con escalado a cero el scheduler no dispara y un rastreo
   largo muere a media ejecución sin dejar rastro. Con CPU siempre asignada se arregla, pero
   entonces se paga lo mismo que una VM con más restricciones.
2. **El ahorro de Cloud Run no era cobrable.** Su ventaja es escalar a cero; como el
   scheduler exige CPU continua, ese descuento no se puede aplicar de todos modos.
3. **El despliegue ya está descrito**: `docker-compose.prod.yml` levanta la aplicación, el
   sandbox aislado y el resto. En una VM es prácticamente `docker compose up -d`; en Cloud Run
   había que descomponerlo en servicios y dar al sandbox su propia VPC.
4. **El sandbox de scripts está diseñado para una red interna sin salida** (`internal: true`).
   Eso funciona tal cual sobre Docker; en Cloud Run es otra pieza que cablear.
5. **Una VM es la forma que tiene un edge node.** Desplegar así ensaya el modo edge mejor que
   Cloud Run, y deja abierta la vía de una VM con GPU si en fase 3 se quiere el modelo local
   para expedientes.

### Lo que NO se autogestiona

**Postgres sigue en Cloud SQL.** Meterlo en un contenedor de la misma máquina convierte al
proyecto en dueño de las copias, del *point-in-time recovery* y de la recuperación ante
pérdida del disco — y lo que hay dentro es el corpus curado y las conversaciones de
ciudadanos. Es la pieza donde el servicio gestionado se paga solo. Igual con **GCS** para los
documentos: `StorageService` ya lo abstrae y sobrevive a que la VM se pierda.

### Dimensionado — MEDIDO el 2026-08-11 (EXT.3)

Medido tras retirar Docling, con `uv sync` aplicado (Docling y RapidOCR **ausentes** del
entorno), sobre Windows con el intérprete del proyecto. Método: `psutil.Process().memory_info().rss`
antes y después de importar `server.app.main`, y de nuevo tras extraer un PDF de 40 páginas.

> **Los tiempos de esta medición NO son trasladables a la VM.** Se tomaron en Windows con la
> caché de disco fría y con el antivirus de por medio; un import de `torch` de 52 s no es lo
> que se verá en Linux, donde suelen ser segundos. **Lo que sí es trasladable es la memoria**,
> y el **orden relativo** entre librerías —que es lo que decide dónde mirar—. El tiempo de
> arranque real hay que volver a medirlo en la máquina, en D.4.

| Medida | Valor |
|---|---|
| RSS tras importar la aplicación | **627 MB** |
| Pico extrayendo un PDF de 40 páginas | **968 MB** (+341 MB sobre el reposo) |
| Tiempo de import de la aplicación | ~131 s (frío) |
| Extracción de 40 páginas con pdfplumber | 17 s / 168.000 caracteres |

**El hallazgo importante: Docling ya no manda, manda `torch`.** Coste de import medido por
librería:

| Librería | Tiempo | RSS |
|---|---|---|
| `transformers` | 142 s | 25 MB |
| `sentence_transformers` | 75 s | 216 MB |
| `torch` | 52 s | 172 MB |
| `pdfplumber` | 0,09 s | 5 MB |

O sea que **pdfplumber es gratis** y lo que queda pesando es la pila de modelos locales
—`torch` + `transformers` + `sentence-transformers`—, que está ahí por `LocalEmbeddingService`
(BGE-M3) y `LocalReranker`, no por la extracción de documentos.

**Consecuencia para D.4.** Si el despliegue usa embeddings de Vertex y el reranker sigue
apagado —que es el plan—, esa pila **no se usa en ejecución** pero se paga entera. Se anotó
como candidato y **se hizo en D.4.0 (2026-08-11)**.

### Resultado de D.4.0 — MEDIDO

`torch`, `torchvision` y `sentence-transformers` pasan al extra `[local-models]`. Además se
descubrió que **`langchain_text_splitters` arrastraba la pila entera**: su `__init__.py`
importa de forma ansiosa un splitter basado en `sentence_transformers` que este proyecto no
usa, y no hay forma de cargar un submódulo sin ejecutar el `__init__` del paquete. El chunker
lo importa ahora dentro del constructor.

| | RSS al importar la app | Arranque | Pila cargada |
|---|---|---|---|
| Antes de D.4.0 | 627 MB | — | `torch`, `transformers`, `sentence_transformers` |
| Con el extra instalado (como corre CI) | **559 MB** | 31,6 s | `torch`, `transformers` |
| **Sin el extra (el despliegue estándar)** | **345 MB** | **9,4 s** | **ninguna** |

**Del arranque estándar se va el 45 % de la memoria.** Y con el extra instalado siguen
cargándose `torch` y `transformers`, pero no por nuestro código: `langchain_core` hace
`try: from transformers import GPT2TokenizerFast / except ImportError` para decidir si sabe
contar tokens. Sin el extra esos paquetes no están, el `except` salta y no se carga nada.

**Para la VM**: con ~345 MB de aplicación más el sandbox y el sistema, **`e2-small` (2 GB) es
holgado**; `e2-medium` solo haría falta si se instalara el extra —o sea, en un edge con
modelos locales—.

---

## Qué cambia en los planes

- **Bloque EXT** (nuevo, 3 prompts): corpus solo `.md`, contexto con pdfplumber, retirada de
  Docling y medición de la huella.
- **Bloque Deploy** reescrito para VM. En particular: **D.1 ya está hecho** —la autenticación
  pública del widget la resolvió SEC.8.5 con la credencial de sitio— y **D.4 deja de desplegar
  tres servicios Cloud Run** (API + embedding-service + docling-service): con embeddings por
  API y sin Docling, es una sola máquina.
- El **ejecutor de trabajos duradero** que SEC.8.8 dejó pendiente para el rastreo **desaparece
  como problema**: en una VM el proceso vive.
