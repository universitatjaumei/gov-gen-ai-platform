"""VER.8 — una regla de selección que no existe no puede aceptarse en silencio.

Al recorrer la publicación se creó una selección con `rule_type='url_prefix'` —inventado, el
real es `path_prefix`— y el endpoint respondió **201**. La regla quedó guardada y
`SelectionRepo.matches` devuelve `False` para cualquier tipo desconocido, así que era una
regla que **no puede casar nunca**: en la pantalla se ve una selección activa y ninguna
página seleccionada, sin nada que explique por qué.

Es el mismo criterio que el proyecto aplica al spider desconocido en
`SiteCrawlerDispatcher`: no caer al genérico ni tragárselo, fallar donde se ve.
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from server.app.modules.curation.selection_contracts import SelectionCreate

TIPOS_REALES = ("path_prefix", "sitemap_section", "manual")


class TestElTipoDeRegla:

    @pytest.mark.parametrize("tipo", TIPOS_REALES)
    def test_should_accept_the_rule_types_the_repo_understands(self, tipo):
        seleccion = SelectionCreate(site_id=uuid.uuid4(), rule_type=tipo, rule_value="/x")

        assert seleccion.rule_type == tipo

    def test_should_refuse_a_rule_type_that_can_never_match(self):
        with pytest.raises(ValidationError) as fallo:
            SelectionCreate(
                site_id=uuid.uuid4(), rule_type="url_prefix", rule_value="https://x/y"
            )

        assert "url_prefix" in str(fallo.value) or "rule_type" in str(fallo.value)
