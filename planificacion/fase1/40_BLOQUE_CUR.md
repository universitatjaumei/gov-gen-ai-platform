## Bloque CUR — La curación como producto propio (PENDIENTE)

> **Contexto**: añadido el 2026-08-02. Decisión completa en `docs/DECISION_CURACION_SEPARADA.md`,
> y reescritura del alcance de 9Q en el encabezado de ese bloque. En una frase: **la curación del
> corpus es una actividad previa, humana y con producto propio; el asistente consume el resultado
> y no lo produce**. 9Q construyó el motor correcto bajo una etiqueta equivocada.
>
> **Este bloque NO reescribe nada.** Es una reorganización: mover módulos, separar la superficie
> de UI y hacer explícito el paso de publicación. El comportamiento del crawler, los detectores y
> los informes no cambia, y el esquema de base de datos **no se toca** —`hub_web_sites`,
> `hub_crawled_pages`, `hub_corpus_selections` y `hub_content_findings` ya están bien modeladas—.
>
> **Por qué va antes del Deploy y no después.** Los artefactos de despliegue codifican la
> estructura: D.4 fija qué imágenes y qué servicios de Cloud Run existen, y D.5 el pipeline que
> los construye. Decidir la clasificación de módulos y routers después de montar eso obliga a
> rehacer parte de D.4/D.5 y a repetir la verificación contra producción. Un refactor pre-deploy
> solo arriesga en local y lo cubren los tests. Va **detrás de CAL.1**, que retira NiceGUI y deja
> menos superficie que mover.
>
> **Lo que este bloque NO hace**: partir el sistema en dos repositorios o dos despliegues. Se
> descarta en la decisión —duplicaría AUTH, tenancy, storage, CI y Orval, y rompería el bucle de
> RAG.14—. Si algún día la curación debe operarla otra unidad, es un perfil más de `DEPLOY_MODE`,
> no un fork.

---

### Prompt CUR.1 (RED/GREEN) — Módulo propio para la curación

**Modelo sugerido**: **Sonnet** — movimiento mecánico con frontera ya decidida; las decisiones abiertas están cerradas en el documento de decisión.

```
# PROMPT CUR.1 (RED/GREEN) — `ingestion/quality/` deja de ser un detalle de la ingesta
# Deploy: edge  (todo el módulo procesa contenido del cliente)

# QUÉ SE MUEVE
#   server/app/modules/agents_hub/ingestion/quality/   →  server/app/modules/curation/
#   server/app/modules/agents_hub/ingestion/spiders/   →  server/app/modules/curation/spiders/
#   server/app/modules/agents_hub/ingestion/spider.py, spider_factory.py  →  idem
#
# QUÉ NO SE MUEVE, Y POR QUÉ
#   - `gap_detector.py` se queda: nace de conversaciones (HubInteraction), no de páginas. Es la
#     señal que el asistente EMITE hacia la curación. Que viva en agents_hub y escriba
#     HubContentFinding con chatbot_id es exactamente el contrato entre las dos mitades.
#   - `chunker`, `watcher`, `docling_processor`, `corpus/`: son la ingesta propiamente dicha,
#     el lado del asistente. La curación produce ficheros que cumplen el contrato del corpus;
#     ingerirlos es trabajo del otro lado.
#   - Las entidades ORM: `HubWebSite` y compañía se quedan en `operational_models.py`. Partir
#     el metadata operacional en dos ficheros no aporta y complica `create_all` de los tests.

# REGLAS
#   - `modules/curation/` NO importa de `agents_hub/agent/` ni de routers cloud. Puede usar
#     `services/embedding_resolver` y `core/` compartidos.
#   - `agents_hub` NO importa de `modules/curation/`. La única comunicación es la tabla
#     `hub_content_findings`, con su CHECK de sujeto único.
#   - `hub_content_quality_router` y `hub_sites_router` se re-etiquetan como routers de curación
#     y se registran igual (`_register_edge`); `Deploy: edge` no cambia.

# TESTS (RED primero)
# tests/modules/curation/test_frontera_curacion.py
# should_not_import_agent_module_from_curation      (grep sobre el árbol, como los guardarraíles de TST)
# should_not_import_curation_from_agents_hub
# should_keep_gap_detector_in_agents_hub            (la señal del uso no se muda)
# + los tests existentes de 9Q se mueven y siguen verdes SIN cambios de aserción

# CRITERIO DE DONE
- [ ] `grep -r "ingestion.quality"` = 0 fuera de `_legacy_*`
- [ ] Suite completa verde; ni una aserción de 9Q reescrita (si hay que tocarlas, el movimiento
      no era mecánico y hay que parar y replantear)
- [ ] Sin migración
```

---

### Prompt CUR.2 (RED/GREEN) — Superficie propia en el frontend y publicación explícita

**Modelo sugerido**: **Sonnet** — reorganización de rutas y navegación con i18n; sin lógica nueva.

```
# PROMPT CUR.2 (RED/GREEN) — La curación deja de ser una pestaña del panel de ingesta

# POR QUÉ
# Mientras el spider viva dentro de la UI de ingesta del chatbot, el producto sigue prometiendo
# «apunta al sitio y el asistente aprende». Esa promesa es la que el corpus normativo desmintió,
# y es peligrosa porque no falla de forma visible: produce respuestas seguras apoyadas en una
# norma derogada.

# QUÉ SE HACE
#   1. `frontend/src/curation/` con navegación propia: Sitios, Auditoría, Hallazgos, Publicación.
#   2. `CorpusSelectionService` sube a primer plano como **paso de publicación**: la pantalla
#      dice qué páginas hay candidatas, quién las aprueba y qué chatbot las recibe. Hoy la
#      operación existe (`ingest_page`) pero está presentada como un detalle técnico.
#   3. Los huecos de corpus de RAG.14 se muestran EN la curación, no solo en el panel del
#      chatbot: son entrada de trabajo para el curador.
#   4. i18n es/ca/en completo. Ninguna cadena nueva hardcodeada.

# LO QUE NO SE HACE
#   - Ningún automatismo de ingesta. Ningún botón «ingerir todo el sitio».
#   - Ninguna lógica de negocio en React: las acciones disponibles vienen del backend.

# TESTS (RED primero)
# should_render_curation_nav_without_chatbot_context
# should_require_explicit_publish_action_per_page
# should_list_corpus_gaps_from_rag14_as_curation_input
# should_have_no_hardcoded_strings            (guardarraíl i18n ya existente, extendido)

# CRITERIO DE DONE
- [ ] `tsc` limpio, Vitest verde, Orval regenerado si cambió el contrato
- [ ] Verificación en navegador por el agente (protocolo de METODOLOGIA_AGENTICA.md §4)
- [ ] Ni un string sin traducir en las tres lenguas
```

---
