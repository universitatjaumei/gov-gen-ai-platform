# Plan de configuración e ingesta de los dos chatbots (pruebas en local)

> **Fecha**: 2026-08-11. **Objetivo**: dejar montados en local el **chatbot público de
> normativa** y el **asistente de Gerencia**, cada uno con su base documental, para probar el
> sistema antes de decidir el despliegue.
>
> Todo lo que sigue está comprobado contra el código y contra las carpetas reales. Donde algo
> está pendiente, se dice que lo está y qué falta exactamente.

---

## 0. Una decisión que hay que tomar ANTES de la primera ingesta

**Con qué proveedor de embeddings se ingiere.** No es un detalle de configuración: el sistema
guarda la procedencia del vector en cada fragmento y `assert_embedding_space_matches` devuelve
**409 en cada consulta** si el corpus se embebió con un modelo y se pregunta con otro. Cambiar
después obliga a **re-embeber el corpus entero**.

**Recomendación: ingerir ya con el proveedor de la API (Google/Vertex)**, el mismo que usará
el despliegue. Razones:

- El ensayo local se parece a producción, que es para lo que sirve un ensayo.
- No hay que re-embeber después.
- Para ~400 documentos el coste de embedding es trivial.
- Encaja con **D.4.0**: si los embeddings van por API, la pila local (`torch`,
  `transformers`, `sentence-transformers`) no hace falta ni en local.

La alternativa —BGE-M3 en local— solo tiene sentido si quieres probar el **modo edge sin
red**. Es un escenario legítimo, pero entonces asúmelo: ese corpus no vale para el despliegue.

---

## 1. Los dos chatbots

|  | **Público — normativa** | **Gerencia — asistente económico-administrativo** |
|---|---|---|
| A quién sirve | Ciudadanía y comunidad universitaria, sin identificar | Personal de Gerencia y unidades administrativas, **identificado** |
| Qué se le pregunta | «¿Cuántos años dura el mandato del Síndic?» | «¿Cómo justifico una dieta de un curso con ingresos externos?» |
| Coste de equivocarse | **Alto**: una cita errónea sale con autoridad de norma ante un tercero | Medio: el funcionario tiene criterio y puede contrastar |
| Superficie | Widget público embebido en la web institucional | Panel interno (frontend propio) |
| Revisión | Detector de huecos (RAG.14) | **Revisión humana de respuestas (REV.1)** — es el motivo del asistente |

La diferencia de fondo, y la que explica casi toda la configuración: **ante el ciudadano es
preferible «no lo sé» a una respuesta plausible mal citada**; ante el funcionario, una
respuesta parcial con su fuente ya es útil.

---

## 2. Configuración recomendada

Todos los campos existen y se resuelven en cascada plataforma → organización → chatbot, así
que lo que sigue se fija **en el chatbot** salvo que se diga otra cosa.

### 2.1 Chatbot público de normativa

| Campo | Valor | Por qué |
|---|---|---|
| `access_mode` | `public_anon` | Sin sesión. **Exige emitir una credencial de sitio** (`/hub/chatbots/{id}/widget-keys`, SEC.8.5) y ponerla en `data-widget-key` del `<script>` |
| `retrieval_mode` | `RAG` | Corpus grande y troceado; el modo de documento entero no cabe |
| `public_graph_profile` | `PUBLIC_KB_RICH` | **No usar `PUBLIC_PORTAL_AGGREGATOR`**: hoy está registrado con UUIDs nulos (stub) y devolvería vacío en silencio |
| `language_mode` | `prefer` | El corpus es bilingüe (188 val / 74 es): la respuesta sigue el idioma de la pregunta y cae al otro si no hay fuente |
| `quality_threshold` | **subir a ~0,7** (default 0,6) | Es el mando que decide cuándo el asistente dice que no sabe. Ante un ciudadano, callar cuesta menos que citar mal |
| `min_retrieval_score` | **subir por encima de 0,0** | El default acepta lo que devuelva la búsqueda vectorial, por flojo que sea. Empieza en 0,3 y ajusta con el dorado |
| `min_retrieval_results` | 2 | Una sola fuente para una respuesta normativa es poco margen |
| `reranker_enabled` | `false` | RAG.6b (Ranking API de Vertex) está pendiente y el reranker local desaparece con D.4.0 |
| `chunking_strategy` | `structural` | Encaja con el contrato: el `.md` ya trae jerarquía y anclas de artículo, y el troceado las respeta |
| `context_token_budget` | heredar (128.000) | Con Gemini por API sobra. **Si algún día se usa un modelo local de 8k, hay que bajarlo aquí** |
| `query_rewriting_enabled` | `false` de entrada | Candidato claro a activar y **medir**: el ciudadano pregunta con sus palabras, no con las de la norma. Pero añade latencia y una llamada |
| `answer_template` | el que exija cita | La advertencia de vigencia y la cita del artículo son el producto, no un adorno |

### 2.2 Asistente de Gerencia

| Campo | Valor | Por qué |
|---|---|---|
| `access_mode` | `restricted` | Exige sesión **y** pertenencia. Es configuración pura, no desarrollo |
| `allowed_saml_groups` | el grupo de Gerencia | Sobre el SSO SAML del bloque AUTH |
| `retrieval_mode` | `RAG` | Igual |
| `public_graph_profile` | `PUBLIC_KB_RICH` | Igual |
| `language_mode` | `prefer` | BOE en castellano, normativa propia bilingüe |
| `quality_threshold` | **bajar a ~0,5** | Al revés que el público: aquí una pista con su fuente ya ayuda, y quien lee sabe contrastar |
| `min_retrieval_score` | ~0,25 | Más permisivo, mismo motivo |
| `reranker_enabled` | `false` | Igual |
| `chunking_strategy` | `structural` | Igual — y **crítico para las FAQ**: un encabezado por pregunta (FAQ.1) |
| `query_rewriting_enabled` | `false` | El personal usa el vocabulario correcto; aquí aporta menos que en el público |
| Revisión | **REV.1** | El veredicto de Gerencia sobre respuestas reales, con cola de pendientes |

---

## 3. Bases documentales

**No comparten corpus.** `HubDocument` tiene unicidad `(chatbot_id, content_hash)`: cada
chatbot lleva su copia de los documentos y de sus embeddings. Lo compartido es el `.md` de
origen.

### 3.1 Público — normativa propia

**Fuente**: `Descarregar_pdf/normativa_propia/publicacio_transparencia_2026-07/md_contracte/`
— **262 documentos**, 188 en valenciano y 74 en castellano; sobre todo Reglaments (162) e
Instruccions (35).

**Estado**: ✅ **listo para ingerir**. Los 262 pasan la validación del pipeline desde que se
corrigió `us_assistents` (2026-08-10). Los defectos que quedan (29 parejas bilingües sin
`canonica`, `content_class` ausente) **no bloquean** una prueba, pero conviene saber que las
parejas entrarán duplicadas y competirán en el top-k.

### 3.2 Gerencia — la carpeta del piloto ya es la curación

**Hallazgo que simplifica el plan**: la carpeta
`openwebui-gerencia/UJI_normativa_piloto_asistente_eco/` **ya es una selección hecha a mano
para este asistente**. No hay que derivar el subconjunto del catálogo de transparencia — y de
hecho **no se podría**: la clasificación nueva (`ambit_principal`, `submateries`) todavía no
existe ni en el front-matter ni en el catálogo (espera a Secretaría General), y el eje viejo
`materia` es el que el contrato prohíbe usar automáticamente por incoherente.

| Carpeta | Contenido | Origen y estado |
|---|---|---|
| `Normativa_general/` | 22 PDF: leyes estatales (`E_`) y de la Generalitat (`GV_`) | **Pendiente**: se generan del XML consolidado, no se convierten del PDF |
| `Normativa_UJI/` | 121 PDF de normativa propia | **Mayormente ya curado**: cruzar con `md_contracte` y reutilizar |
| `Manuales/` | 5 PDF, incluida `Preguntas_frecuentes_UGITJ.pdf` | **Pendiente**: la FAQ necesita el formato de FAQ.1 |
| `Delegaciones_competencias_firmas/` | 5 PDF | Pendiente de decidir si entran |
| `Nombramientos/` | 3 PDF | Probablemente **no**: son actos, no normativa consultable |

---

## 4. Lo que falta por fuente, y qué hacer

### 4.1 Normas del BOE y del DOGV (22 documentos) — PENDIENTE

El contrato es explícito: **«Para BOE y DOGV no se escribe el `.md` a mano. Se genera desde el
XML consolidado.»** Y hay una razón práctica además de la formal: el consolidado trae el texto
**vigente hoy**, con sus modificaciones aplicadas. Convertir el PDF daría la versión del día
en que se publicó, que para la Ley de Contratos o la LPAC está desfasada — y ese es
exactamente el error que un asistente normativo no puede cometer.

**Lo pendiente**: la descarga del XML/TXT consolidado. Reparto real de la carpeta:

- **12 estatales (`E_`)** → BOE, API de legislación consolidada.
- **8 de la Generalitat (`GV_`)** → DOGV.
- **2 casos especiales**: `Carta_europea_investigador.pdf` (no es BOE ni DOGV) y
  `Criterios para la gestión de ingresos en la UJI.pdf` (normativa propia → va por el pipeline
  de curación, no por aquí).

**Para la prueba en local no hace falta esperar a las 22.** Con **tres o cuatro** —la LCSP, la
LPAC, el RD de indemnizaciones y la Ley de subvenciones— ya se puede medir si el asistente
responde bien a preguntas de gestión económica.

### 4.2 La FAQ de UGITJ — PENDIENTE, y es un PDF

`Preguntas_frecuentes_UGITJ.pdf` (117 KB) **no se puede subir tal cual**: desde EXT.1 al corpus
solo entra `.md`. Y además necesita el formato de **FAQ.1**: `content_class: faq` y **un
encabezado por pregunta** con su ancla, para que cada pregunta y su respuesta caigan en el
mismo fragmento. Si va en negritas o en lista, un corte deja media pregunta con la respuesta
de otra, y eso se cita mal sin que se note.

Dos caminos:

1. **Ejecutar FAQ.1 primero** y convertir siguiendo el formato que fije. Es lo correcto.
2. **Escribir el `.md` a mano** siguiendo el formato ya descrito en el prompt FAQ.1. Para un
   PDF de 117 KB es asumible y desbloquea la prueba sin esperar.

En los dos casos, **la FAQ es lo que más va a lucir** en el asistente: el texto de la pregunta
es un objetivo de embedding casi perfecto, porque se parece a lo que el funcionario escribe
mucho más que el artículo que la fundamenta.

### 4.3 Los manuales (GRE, Kalendas, presupuesto, identidad visual)

Son manuales de procedimiento, no normativa. **Recomendación**: entran, pero como
`content_class: generic`, y **no** el de identidad visual corporativa (6,8 MB, es una guía de
diseño; no responde preguntas de gestión y solo añade ruido al índice).

Convertirlos exige el pipeline de curación. Para la primera prueba **pueden esperar**: con la
FAQ y las normas generales ya hay material suficiente para juzgar el asistente.

---

## 5. Procedimiento de ingesta, en orden

```
# 0. Prerrequisitos
docker compose up -d          # BD arriba
cd server; uv run alembic upgrade head

# 1. Vocabulario (una vez por organización) — ver docs/CARGA_VOCABULARIO.md
#    Primero ambit, luego submateria: el orden importa.

# 2. Crear los dos chatbots por el panel, con la configuración de la sección 2.
#    Anotar sus UUID.

# 3. Corpus del público (262 normas propias)
uv run python -m server.app.modules.agents_hub.ingestion.corpus.load \
    --dir <...>/md_contracte --chatbot-id <UUID_PUBLICO> --dry-run
#    y luego sin --dry-run

# 4. Corpus de Gerencia: MISMO comando, subconjunto distinto y otro chatbot
#    (el subconjunto sale de cruzar la carpeta del piloto con md_contracte)
uv run python -m ...corpus.load --dir <dir_gerencia> --chatbot-id <UUID_GERENCIA>

# 5. Credencial de sitio del chatbot público (para el widget)
#    POST /hub/chatbots/<UUID_PUBLICO>/widget-keys  -> se muestra UNA vez
```

**Comprobación después de cada ingesta**: que el recuento de documentos y fragmentos cuadre, y
una consulta real que devuelva cita con su artículo.

---

## 6. Imágenes y datos: comprobado

Lo que preguntabas está bien resuelto, y lo he verificado:

- **El contenedor de la aplicación no monta ningún volumen** en `docker-compose.prod.yml`. Es
  desechable por diseño: se puede reconstruir y reemplazar sin perder nada.
- **Los datos viven en volúmenes con nombre**: `postgres_data_prod` (base) y `minio_data_prod`
  (documentos). Los volúmenes con nombre **sobreviven** a `docker compose down`, a
  `docker compose pull` y a la reconstrucción de imágenes.
- **Los documentos no tocan el disco del contenedor**: `StorageService` (fsspec) los escribe
  en MinIO en local y en GCS en producción.

**Un aviso y una confirmación:**

⚠️ `docker compose down -v` **sí borra los volúmenes**. Es la única forma de perder los datos
por accidente, y basta con no usar `-v`.

✅ En el despliegue en VM el problema desaparece del todo: la base va a **Cloud SQL** y los
documentos a **GCS**, así que la máquina no guarda nada que duela perder. Eso es deliberado —
D.4-VM lo dice explícitamente— y es lo que permite reaprovisionar la VM entera sin plan de
recuperación.

**Y una prueba de que el principio se vigila**: la auditoría encontró que los temas visuales se
escribían en `data/themes`, una ruta local del contenedor. En Cloud Run habrían desaparecido al
reciclarse la instancia, llevándose por delante el tema del widget. **SEC.8.6 lo movió a la
base de datos.** No era teoría: era un caso real de dato colado dentro de la imagen.

---

## 7. Qué bloquea qué

| Para... | Hace falta | Estado |
|---|---|---|
| Probar el chatbot **público** | Vocabulario + `md_contracte` + chatbot creado + credencial de sitio | ✅ **Se puede hacer ya** |
| Probar el asistente de **Gerencia** con normativa propia | Subconjunto del piloto cruzado con `md_contracte` | ✅ Se puede hacer ya |
| Que Gerencia responda con **FAQ** | `.md` de FAQ en formato FAQ.1 | ⏳ FAQ.1, o `.md` a mano |
| Que Gerencia cite **BOE/DOGV** | XML consolidado descargado y convertido | ⏳ Descarga pendiente |
| Que Gerencia **revise** las respuestas | REV.1 | ⏳ Pendiente |
| Fijar el tamaño de la VM | D.4.0 | ⏳ Pendiente |

**Camino más corto a una prueba útil**: público con las 262 normas + Gerencia con el
subconjunto propio y la FAQ escrita a mano. Eso ya permite comparar dos configuraciones sobre
material real, que es lo que la prueba tiene que responder.
