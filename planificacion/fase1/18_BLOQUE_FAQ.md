## Bloque FAQ — Preguntas frecuentes como contenido citable (PENDIENTE)

> **Contexto**: decisión del 2026-08-11. Algunos chatbots deben responder a partir de un
> documento de **preguntas frecuentes con respuesta sugerida**. Se descartaron las otras dos
> vías que se plantearon:
>
> - **Como ejemplos en el prompt**: no escala —cien FAQ no caben en un prompt de sistema— y
>   además invita al modelo a parafrasear una respuesta institucional, que es justo lo que no
>   debe hacer con un texto que alguien redactó con cuidado.
> - **Como dataset dorado**: el dorado mide **recuperación**; es un artefacto de prueba, no
>   de contenido. (Pero ver FAQ.2: el mismo fichero puede sembrarlo, y eso es gratis.)
>
> **Se ingieren como documentos**, con `content_class: faq` —valor que el contrato ya admite—.
> La razón de fondo no es la comodidad: **el texto de la pregunta de una FAQ es un objetivo de
> embedding casi perfecto**, porque se parece mucho más a lo que el ciudadano escribe que el
> artículo que la fundamenta. Una FAQ recupera mejor que su propia norma.
>
> **El riesgo que este bloque tiene que cerrar**: una respuesta sugerida **no es una norma**.
> Si se cita con la misma autoridad que un artículo, se habrá publicado una respuesta no
> revisada como si fuera normativa.

---

### Prompt FAQ.1 (RED/GREEN) — Formato del `.md` de preguntas frecuentes y su troceado

**Modelo sugerido**: **Sonnet** — extiende un contrato que ya existe; el troceador ya es por
encabezados y no hay que tocarlo si el formato se define bien.

**Objetivo**: fijar cómo se escribe un `.md` de FAQ para que cada pregunta y su respuesta
acaben en **el mismo fragmento**, y ni una pregunta se separe de su respuesta ni se mezcle con
la de al lado.

```
# PROMPT FAQ.1 (RED/GREEN) — Una pregunta, un encabezado, un fragmento
# Deploy: edge

## El formato (se añade como sección propia a docs/CONTRATO_MD_CORPUS.md)
- Front-matter con `content_class: faq` y el resto de campos del contrato como cualquier
  documento (`language`, `id_publicacio`, `title`, `estat_vigencia`...).
- **Un encabezado de unidad citable por pregunta**, con su ancla: la pregunta ES el
  encabezado. Ancla estable con prefijo propio, `{#faq-N}`, para que una cita apunte a la
  pregunta y no al documento entero.
- La respuesta sugerida, en el cuerpo de esa unidad.
- **Referencia a la norma que la sostiene**, cuando la haya: es lo que permite que la
  respuesta remita al artículo en vez de sustituirlo.

## Por qué así, y no con negritas o listas
El troceador parte por encabezados (5 niveles + anclas). Si las preguntas van en negrita o en
una lista, el documento entero cae en uno o dos fragmentos y la recuperación devuelve un
bloque con veinte preguntas, de las que diecinueve no vienen a cuento. Peor todavía: un corte
en mitad de la lista deja media pregunta con la respuesta de otra, y **eso se cita mal sin que
se note**.

## Tests (RED primero)
# should_chunk_one_question_and_its_answer_together
# should_not_merge_two_consecutive_questions_in_one_chunk
# should_keep_the_faq_anchor_in_the_chunk_metadata
# should_reject_a_faq_document_whose_questions_are_bold_instead_of_headings
#     (con un aviso que diga por qué: es el error que se va a cometer)
# should_accept_a_faq_document_that_conforms   (extremo a extremo: sube, trocea, recupera)

## Cierre
- [ ] La sección del formato está en `docs/CONTRATO_MD_CORPUS.md`, con un ejemplo completo
- [ ] Un `.md` de FAQ de ejemplo, ingerible, en el repositorio o en el proyecto de curación
```

---

### Prompt FAQ.2 (RED/GREEN) — Una FAQ se cita como FAQ, nunca como norma

**Modelo sugerido**: **Opus** — toca el contrato de citas y la plantilla de respuesta, que es
donde se decide qué autoridad se le atribuye a un texto ante un ciudadano. Equivocarse aquí no
produce un error visible.

**Objetivo**: que la respuesta y la cita distingan una respuesta sugerida de un artículo de
norma. `content_class` ya lo modela; falta que llegue hasta la salida.

```
# PROMPT FAQ.2 (RED/GREEN) — La autoridad del texto viaja con el fragmento
# Deploy: edge

## Cambios
- El `content_class` del documento llega al metadato del fragmento y de ahí a la evidencia
  que consume el grafo. Hoy el troceador ya propaga `estat` y `classes`; es el mismo camino.
- Contrato de citas (P6): una fuente `faq` se presenta como **respuesta orientativa**, con su
  etiqueta, y —si la declara— con el enlace a la norma que la sostiene. Nunca con la misma
  forma que una cita de artículo.
- Plantilla de respuesta: cuando la evidencia dominante es `faq`, el texto debe decir que es
  orientativa. Sin inventar un aviso legal: una frase, y el enlace a la norma.

## Lo que se anunció como «regalo gratis» y NO lo era (comprobado al ejecutar)
- **Sembrar el dataset dorado desde el fichero de FAQ**: **descartado, no es gratis.** Un
  `GoldenQuery` es consulta + documentos que deberían salir. Si el objetivo de la pregunta de
  una FAQ es **la propia FAQ**, la entrada es circular y no mide nada: el documento que
  contiene literalmente esa frase la recupera siempre. Lo que sí valdría —pregunta de FAQ →
  **la norma** que la sostiene— exige mapear la referencia de respaldo a un identificador de
  documento, y eso no existe al escribir la FAQ. Queda como candidato cuando el respaldo se
  declare de forma estructurada, no como texto.
- **Alimentar el detector de huecos (RAG.14)**: no hace falta código. El detector ya trabaja
  sobre las conversaciones con `fallback_reason`; una FAQ que el corpus no sabe responder
  aparece sola en cuanto alguien la pregunta. Era una observación operativa disfrazada de
  tarea.

## Tests (RED primero)
# should_label_a_faq_source_as_orientative_in_the_citation
# should_not_present_a_faq_with_the_same_shape_as_an_article_citation
# should_link_to_the_backing_regulation_when_the_faq_declares_one
# should_carry_content_class_from_document_to_chunk_metadata
# should_mark_faq_evidence_in_the_packed_context   (el aviso va DENTRO del texto que ve el
#     modelo: marcarlo solo en el JSON deja que la respuesta presente la sugerencia como
#     norma, con una etiqueta al lado que la contradice)

## Cierre
- [ ] Una respuesta apoyada en FAQ es distinguible de una apoyada en norma **leyéndola**,
      no solo inspeccionando el JSON
```

---
