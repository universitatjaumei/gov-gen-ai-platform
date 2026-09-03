## Bloque LANG — Política de lengua configurable: monolingüe y respuesta fija (PENDIENTE, planificado el 2026-09-01)

> **Posición**: independiente de Deploy; dos prompts. Conviene ejecutarlo **antes del primer
> despliegue para una organización monolingüe** (el escenario ayuntamientos): el mando ya existe
> en la cascada, pero está desconectado.

**Origen**: pregunta del usuario del 2026-09-01 («¿se puede construir un grafo sin selector de
idiomas, para ayuntamientos que no sean multilingües?»). La respuesta medida contra el código: el
grafo no se construye «con o sin» nodo de lengua — la política de lengua es una **estrategia**
del CoreGraph y sobre corpus monolingüe degrada sola a passthrough (la ordenación por lengua no
reordena, la segunda búsqueda no se lanza, el aviso de traducción no salta) —, pero al
verificarlo aparecieron **dos huecos**:

1. **`language_mode` viaja por toda la cascada y nadie lo consume.** Plataforma (`prefer`) →
   `HubOrganizacion.default_language_mode` → `HubChatbot.language_mode` →
   `PublicGraphConfig.language_mode`… y la factoría del perfil monta siempre
   `DefaultLanguagePolicy` (`graph_factory.py`, `_make_public_kb_rich`). El valor `"none"` está
   documentado en `metadata_filter.py` («sin regla de lengua») y no hay ningún `if` que lo lea.
2. **El modo que pediría una organización monolingüe no existe**: «responde siempre en X,
   pregunten como pregunten». Hoy el grafo detecta la lengua de la pregunta e instruye «Responde
   en {esa}»: a quien pregunte en catalán a un ayuntamiento castellanohablante se le contesta en
   catalán, sin que el organismo tenga dónde decidir lo contrario.

**Reglas del bloque**:

- **Tres modos y solo tres**: `prefer` (el actual, sigue siendo el defecto), `none` (sin
  política: sin detección, sin orden por lengua, sin instrucción de lengua en el prompt) y
  `fixed:<código>` (instruye siempre esa lengua y prefiere esa versión del corpus, sin detectar).
- **Las políticas nuevas implementan el protocolo `LanguagePolicy` existente**; el CoreGraph no
  se toca. Lo único que cambia es qué política compone la factoría según `cfg.language_mode`.
- **El modo es dato en cascada, nunca un perfil distinto**: un despliegue monolingüe es
  configuración del mismo grafo, no otro grafo. Es el argumento dado a desarrollo («framework,
  no generador») y este bloque es lo que lo hace verdad también aquí.

---

### Prompt LANG.1 (RED/GREEN) — Cablear `language_mode`: `none` y `fixed:<lang>`

**Modelo sugerido**: **Sonnet** — alcance cerrado: dos clases pequeñas sobre un protocolo
existente y un branch en la factoría.

**Objetivo**: que `cfg.language_mode` decida la política de lengua que compone `GraphFactory`,
con los tres modos, y que el valor se valide al escribirse.

**Instrucciones al agente**:
```markdown
# PROMPT LANG.1 (RED/GREEN) — language_mode deja de estar desconectado

## Políticas (junto a PreferLanguagePolicy, en strategies/protocols.py)
- NoneLanguagePolicy: detect() -> None. Con None todo lo demás ya degrada solo:
  needs_secondary_search devuelve False, filter_items es passthrough y el prompt no
  lleva "Responde en".
- FixedLanguagePolicy(lang): detect() -> lang SIEMPRE, sin mirar la consulta (sin
  langdetect). El efecto aguas abajo es el correcto sin tocar CoreGraph: "Responde en
  {lang}" en el prompt y query_language={lang} en la recuperación (prefiere esa versión
  de una norma bilingüe).

## Factoría (core/graph_factory.py, _make_public_kb_rich)
- language_mode == "none"            -> NoneLanguagePolicy
- language_mode.startswith("fixed:") -> FixedLanguagePolicy(código)
- resto                              -> DefaultLanguagePolicy (comportamiento actual intacto)

## Validación del valor (en los contratos de chatbot y organización del router)
- "prefer" | "none" | "fixed:<código de 2-3 letras minúsculas>"; cualquier otro valor
  -> 422 con mensaje que enumere los modos. Hoy es String(20) libre: un typo caería a
  prefer sin avisar a nadie.

## Tests (mínimo 6) — tests/public_graphs/test_lang1_language_mode.py
- none: el prompt final NO contiene "Responde en" y no se lanza segunda búsqueda.
- fixed:es con pregunta en catalán: el prompt instruye responder en es.
- fixed:es: la recuperación recibe query_language="es".
- prefer: comportamiento idéntico al actual (test de regresión).
- El branch de la factoría con los tres valores.
- 422 del endpoint con language_mode="castellano".
```

**Verificación**: suite de `tests/public_graphs/` + `tests/infra/test_suite_hygiene.py` verdes; y
una conversación real contra un chatbot puesto en `fixed:es` preguntando en catalán, respondida
en castellano (evidencia en el informe de cierre).

---

### Prompt LANG.2 — El modo de lengua en el panel

**Modelo sugerido**: **Sonnet** — UI sobre contrato cerrado en LANG.1.

**Objetivo**: exponer el modo en la interfaz de administración (por chatbot y el defecto por
organización), con i18n y verificación en navegador.

**Instrucciones al agente**:
```markdown
# PROMPT LANG.2 — desplegable de modo de lengua en ChatbotsPage y en la organización

- Desplegable con los tres modos; al elegir fixed, selector del código de lengua. El
  catálogo de modos NO se hardcodea en React: viene del contrato OpenAPI (enum) o de un
  endpoint — regla maestra de contract-first.
- i18n es/ca/en para etiquetas y descripciones cortas de cada modo (qué implica elegirlo).
- Orval regenerado si el contrato cambió en LANG.1.
- Tests de frontend: el desplegable se construye desde el contrato; guardar envía el valor;
  el valor actual se muestra.
- Verificación en navegador: cambiar un chatbot a fixed:es, conversar en catalán desde el
  widget, respuesta en castellano; read_console_messages y read_network_requests limpios.
```

**Al cerrar el bloque**: suite completa desde Git Bash; actualizar `docs/` si existe guía de
configuración de chatbots que enumere los campos.

---
