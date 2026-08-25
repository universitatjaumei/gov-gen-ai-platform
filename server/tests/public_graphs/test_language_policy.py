"""Tests de LanguagePolicy — 9B.12 (RED/GREEN).

Verifican que:
- prefer: no hace doble búsqueda si ya hay evidencia en el idioma del usuario.
- strict: filtra items al idioma del usuario; si quedan vacíos → calidad 0 → fallback.
- El warning de traducción sólo se activa cuando context_source_language != query_language
  (señal independiente de fallback_triggered).
"""
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    NeutralLanguagePolicy,
    PreferLanguagePolicy,
    StrictLanguagePolicy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)

_ITEM_ES = EvidenceItem(source_id="doc-es", content="Contenido en español.", language="es")
_ITEM_CA = EvidenceItem(source_id="doc-ca", content="Contingut en català.", language="ca")
_ITEM_NO_LANG = EvidenceItem(source_id="doc-nl", content="Sin idioma.")


class TestPreferLanguagePolicy:

    def test_language_policy_prefer_avoids_double_search(self):
        """prefer: no hace segunda búsqueda si ya existe evidencia en el idioma del usuario."""
        policy = PreferLanguagePolicy()

        # Hay items en el idioma del usuario → no se necesita doble búsqueda
        assert policy.needs_secondary_search("es", [_ITEM_ES, _ITEM_CA]) is False
        assert policy.needs_secondary_search("ca", [_ITEM_ES, _ITEM_CA]) is False

        # No hay items en el idioma del usuario → sí se necesita doble búsqueda
        assert policy.needs_secondary_search("ca", [_ITEM_ES]) is True
        assert policy.needs_secondary_search("en", [_ITEM_ES, _ITEM_CA]) is True

    def test_prefer_no_secondary_search_when_language_unknown(self):
        """prefer: sin idioma detectado nunca lanza búsqueda secundaria."""
        policy = PreferLanguagePolicy()
        assert policy.needs_secondary_search(None, [_ITEM_ES]) is False
        assert policy.needs_secondary_search(None, []) is False

    def test_prefer_filter_items_returns_all(self):
        """prefer no filtra items: no pierde ninguno.

        **VIS.4 cambió el orden a propósito**, así que este test ya no puede comparar la lista
        entera: la preferencia de lengua pasa a operar *dentro* de la misma vigencia —primero lo
        vigente, después la lengua—, y eso reordena. Lo que sigue siendo cierto, y es lo que
        distingue `prefer` de `strict`, es que **no se descarta evidencia**.
        """
        policy = PreferLanguagePolicy()
        items = [_ITEM_ES, _ITEM_CA, _ITEM_NO_LANG]

        assert sorted(
            policy.filter_items("ca", items), key=id
        ) == sorted(items, key=id)
        # Sin lengua de pregunta no hay nada que priorizar, así que ni siquiera se reordena.
        assert policy.filter_items(None, items) == items


class TestStrictLanguagePolicy:

    def test_language_policy_strict_can_trigger_fallback(self):
        """strict filtra al idioma del usuario; items vacíos → quality_score=0 → fallback."""
        policy = StrictLanguagePolicy()

        # Consulta en catalán, items sólo en español → sin match → lista vacía
        filtered = policy.filter_items("ca", [_ITEM_ES])
        assert filtered == [], (
            "strict debe filtrar items que no coincidan con query_language; "
            "lista vacía dispara fallback vía quality_gate"
        )

        # Consulta en español, items en español → pasan el filtro
        filtered_es = policy.filter_items("es", [_ITEM_ES, _ITEM_CA])
        assert len(filtered_es) == 1
        assert filtered_es[0].language == "es"

    def test_strict_no_secondary_search(self):
        """strict no hace doble búsqueda: filtra y acepta fallback si quedan pocos items."""
        policy = StrictLanguagePolicy()
        assert policy.needs_secondary_search("ca", [_ITEM_ES]) is False

    def test_strict_filter_passthrough_when_language_unknown(self):
        """strict sin idioma detectado pasa todos los items sin filtrar."""
        policy = StrictLanguagePolicy()
        items = [_ITEM_ES, _ITEM_CA]
        assert policy.filter_items(None, items) == items


class TestNeutralLanguagePolicy:

    def test_neutral_no_filtering_and_no_warning(self):
        """none: no filtra, nunca avisa de traducción."""
        policy = NeutralLanguagePolicy()
        items = [_ITEM_ES, _ITEM_CA]
        assert policy.filter_items("ca", items) == items
        assert policy.needs_secondary_search("ca", [_ITEM_ES]) is False
        assert policy.should_warn_translation("ca", "es") is False


class TestTranslationWarning:

    def test_warning_only_when_context_language_differs(self):
        """El warning sólo se emite cuando context_source_language != query_language."""
        policy = PreferLanguagePolicy()

        # Idiomas distintos → warning
        assert policy.should_warn_translation("ca", "es") is True
        assert policy.should_warn_translation("es", "ca") is True

        # Idiomas iguales → sin warning
        assert policy.should_warn_translation("es", "es") is False
        assert policy.should_warn_translation("ca", "ca") is False

    def test_no_warning_when_language_unknown(self):
        """Sin idioma de consulta o contexto no se puede emitir warning."""
        policy = PreferLanguagePolicy()
        assert policy.should_warn_translation(None, "es") is False
        assert policy.should_warn_translation("es", None) is False
        assert policy.should_warn_translation(None, None) is False

    def test_warning_independent_of_fallback(self):
        """El warning de traducción es una señal independiente de fallback_triggered.

        should_warn_translation evalúa sólo los idiomas; no recibe ni consulta
        ningún indicador de calidad ni de fallback.
        """
        policy = PreferLanguagePolicy()
        # La firma del método no acepta fallback_triggered: si los idiomas difieren,
        # always True; si coinciden, always False — sin importar el estado del grafo.
        assert policy.should_warn_translation("ca", "es") is True
        assert policy.should_warn_translation("es", "es") is False
