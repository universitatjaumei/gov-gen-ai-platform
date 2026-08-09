"""Curación del corpus: producto propio, previo al asistente (CUR.1).

`docs/DECISION_CURACION_SEPARADA.md`: el crawler y los detectores de incoherencias son
herramientas de curación, no de ingesta. Ayudan a un humano a decidir qué entra al corpus y
detectan qué está mal publicado; no alimentan el corpus por sí solos.

Frontera con `agents_hub` (vigilada por `tests/modules/curation/test_frontera_curacion.py`):

- `curation` NO importa de `agents_hub/agent/` (el grafo LangGraph) ni de routers cloud.
  Puede usar `agents_hub/services/embedding_resolver` y `core/` compartidos.
- `agents_hub` NO importa de `curation`. La única comunicación entre las dos mitades es la
  tabla `hub_content_findings`, con su CHECK de sujeto único (`site_id` XOR `chatbot_id`).
- `gap_detector.py` (huecos de corpus, RAG.14) vive en `agents_hub/ingestion/`, no aquí:
  nace de conversaciones, no de auditar páginas — es la señal que el asistente EMITE hacia
  la curación.
"""
