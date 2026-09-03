## Bloque DET — Desempate determinista del retriever (PENDIENTE)

> **Contexto**: añadido el 2026-08-02 al cuadrar la deuda del cierre del Bloque RAG. La baseline del gate
> se movió de 0,920 a 0,940 sin que nadie tocara el ranking, y la causa medida no fue una mejora: es un
> **empate exacto de coseno** (`0,316227773316`) entre dos fragmentos de documentos distintos en una de las
> 25 consultas del dorado. `vector_search` y `keyword_search` ordenan **solo por puntuación**, sin desempate,
> así que cuál de los dos empatados queda primero lo decide el plan de la consulta. Refutadas por medición
> las tres explicaciones que parecían obvias: HNSW (con 52 filas el planificador ni lo toca), el índice
> `ix_hub_document_chunks_embedding_space` de RAG.9 (quitarlo no cambia nada) y la anchura de fila.
>
> **Por qué es de producción y no de tests**: cuando dos fragmentos empatan, hoy decide el planificador
> **qué norma se cita**. En un asistente normativo la evidencia mostrada no es presentación, es la respuesta.
> Que el gate deje de tener margen cero es la propina, no el motivo.
>
> **La restricción dura, medida antes de escribir el prompt**: un desempate en el `ORDER BY` de la rama
> vectorial **inutiliza el índice HNSW**. pgvector solo sirve el índice para `ORDER BY <distancia>` a secas.
>
> ```
> ORDER BY embedding <=> $1 LIMIT 10        →  Index Scan using ix_hub_document_chunks_embedding_hnsw
> ORDER BY embedding <=> $1, id LIMIT 10    →  Seq Scan + Sort   (con enable_seqscan=off: no hay alternativa)
> ```
>
> O sea que la solución evidente deshace RAG.3 y devuelve cada consulta a recorrer todos los chunks del
> chatbot. De ahí que el desempate vaya **en SQL en la rama léxica y en Python en la vectorial**.

---

### Prompt DET.1 (RED/GREEN) — Desempate estable en las dos ramas del híbrido

**Modelo sugerido**: **Sonnet** — el alcance está cerrado y las dos decisiones de diseño (dónde desempatar en cada rama, y con qué columna) vienen ya decididas y medidas en el contexto del bloque.

```
# PROMPT DET.1 (RED/GREEN) — El orden del retriever deja de depender del plan de la consulta
# Deploy: edge  (el retriever es edge; no toca configuración ni routers cloud)

# QUÉ SE ARREGLA
# Dos fragmentos con la misma puntuación salen hoy en el orden que quiera el planificador.
# Tras este prompt salen siempre en el mismo, y ese orden sobrevive a una reingesta.

# LAS TRES PIEZAS

# 1. Rama léxica (`keyword_search`): desempate EN SQL.
#    `ts_rank_cd` devuelve valores muy cuantizados y los empates son frecuentes — y lo seguirán
#    siendo con el corpus real, no son artefacto del fixture. El GIN sirve el WHERE, no el
#    ORDER BY, así que ese Sort ya se paga hoy: la segunda clave es gratis.
#        stmt.order_by(rank.desc(), HubDocumentChunk.content_hash)

# 2. Rama vectorial (`vector_search`): desempate EN PYTHON, DESPUÉS del LIMIT.
#    El SQL se queda EXACTAMENTE como está — HNSW intacto, ver la restricción del bloque — y se
#    reordena el conjunto ya devuelto antes de construir los SearchResult. Son top_k*2 filas,
#    unas 20-30: coste nulo.
#    RESIDUO QUE SE ACEPTA Y SE DOCUMENTA EN EL DOCSTRING: si un empate cae justo en el borde
#    del LIMIT, qué filas vuelven sigue dependiendo del plan. Con BGE-M3 es teórico (empates
#    exactos entre floats de 1024 dimensiones no ocurren); con el embedding determinista del
#    fixture es el caso común, pero el borde concreto es raro. No se arregla porque arreglarlo
#    cuesta el índice.

# 3. La clave de desempate es `content_hash`, NO `id`.
#    `id` es un uuid4: determinista dentro de una ingesta y ARBITRARIO entre reingestas, así que
#    cada recarga del corpus rebarajaría los empates y tendríamos el mismo problema con otra cara.
#    `content_hash` del chunk se deriva de su propio contenido (`watcher.py`, `hash_content(ch.content)`),
#    o sea que es estable entre reingestas y entre máquinas.

# TESTS (RED primero)
# tests/modules/agents_hub/integration/test_retriever_desempate.py
# should_break_vector_ties_by_content_hash          (dos chunks con embedding idéntico)
# should_break_keyword_ties_by_content_hash         (dos chunks con el mismo ts_rank_cd)
# should_keep_the_same_order_across_plans           (mismo resultado con enable_seqscan on/off)
# should_not_reorder_results_that_do_not_tie        (el desempate no toca lo que ya está ordenado)
# should_keep_hnsw_usable_by_the_vector_branch      (EXPLAIN: el ORDER BY vectorial sigue a secas)

# CRITERIO DE DONE
- [ ] Los 5 tests en verde + `tests/modules/agents_hub` sin regresiones
- [ ] `EXPLAIN` en el test demuestra que la rama vectorial sigue pudiendo usar HNSW
- [ ] Baseline del gate regenerada DESPUÉS del cambio (`GOLDEN_UPDATE_BASELINE=1`): la cifra que
      salga —0,940 o 0,920— ya es estable, y la `nota` del fichero deja de advertir del empate
- [ ] Sin migración: no hay cambio de esquema
```

---
