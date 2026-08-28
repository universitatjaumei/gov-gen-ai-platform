"""ACT.6 — el descriptor y el plan, que es lo que se lee antes de decir que sí.

La reconciliación se prueba en `test_corpus_reconciler.py`; aquí sólo lo que ACT.6 añade: leer
el descriptor sin equivocarse y **enseñar por separado lo que cambia de estado**.

Por qué ese bloque va aparte: un `= (metadatos)` se lee igual tanto si se corrige un resumen
como si una norma se apaga. Así fue como las 22 normas externas volvieron a encenderse en el
asistente normativo sin que nadie lo hubiera decidido — estaban entre 292 líneas idénticas.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.modules.agents_hub.ingestion.corpus.actualiza import (
    DescriptorInvalido,
    leer_descriptor,
    resumen,
)


def _escribir(tmp_path, texto: str):
    ruta = tmp_path / "descriptor.yaml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


class TestElDescriptor:

    def test_should_keep_the_declared_order(self, tmp_path):
        """El orden es parte del descriptor: con Normativa delante, Gerencia copia."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        ruta = _escribir(tmp_path, f"""
paquetes:
  - nom: normatiu
    dir: {(tmp_path / 'a').as_posix()}
    chatbots: ["{uuid.uuid4()}"]
  - nom: gerencia
    dir: {(tmp_path / 'b').as_posix()}
    chatbots: ["{uuid.uuid4()}", "{uuid.uuid4()}"]
""")

        paquetes = leer_descriptor(ruta)

        assert [p.nom for p in paquetes] == ["normatiu", "gerencia"]
        assert len(paquetes[1].chatbots) == 2

    def test_should_reject_a_chatbot_declared_twice(self, tmp_path):
        """Casi siempre es copiar y pegar, y su efecto no se ve hasta que falta normativa."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        repetido = uuid.uuid4()
        ruta = _escribir(tmp_path, f"""
paquetes:
  - nom: normatiu
    dir: {(tmp_path / 'a').as_posix()}
    chatbots: ["{repetido}"]
  - nom: gerencia
    dir: {(tmp_path / 'b').as_posix()}
    chatbots: ["{repetido}"]
""")

        with pytest.raises(DescriptorInvalido, match="ya estaba"):
            leer_descriptor(ruta)

    def test_should_reject_a_directory_that_is_not_there(self, tmp_path):
        ruta = _escribir(tmp_path, f"""
paquetes:
  - nom: normatiu
    dir: {(tmp_path / 'no-existe').as_posix()}
    chatbots: ["{uuid.uuid4()}"]
""")

        with pytest.raises(DescriptorInvalido, match="no es un directorio"):
            leer_descriptor(ruta)

    def test_should_reject_a_package_without_chatbots(self, tmp_path):
        (tmp_path / "a").mkdir()
        ruta = _escribir(tmp_path, f"""
paquetes:
  - nom: normatiu
    dir: {(tmp_path / 'a').as_posix()}
    chatbots: []
""")

        with pytest.raises(DescriptorInvalido, match="ningun chatbot"):
            leer_descriptor(ruta)

    def test_should_reject_an_empty_descriptor(self, tmp_path):
        with pytest.raises(DescriptorInvalido, match="ningun paquete"):
            leer_descriptor(_escribir(tmp_path, "paquetes: []\n"))


class TestElPlanSeparaLoQueCambiaDeEstado:

    def _informe(self, **kwargs):
        from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
            ReconcileReport,
        )

        return ReconcileReport(**kwargs)

    def test_should_show_state_changes_in_their_own_block(self):
        informe = self._informe(
            metadatos_actualizados=270,
            cambios_de_estado=["EXT-001: us_assistents: no -> si"],
            detalle=["! ext.md (us_assistents: no -> si)"],
        )

        texto = resumen("normatiu", "cb", informe)

        assert "CAMBIOS DE ESTADO" in texto
        assert "EXT-001: us_assistents: no -> si" in texto
        assert "metadatos sin efecto en la recuperacion: 270" in texto

    def test_should_never_truncate_the_state_changes(self):
        """Los nuevos se resumen; los cambios de estado se leen enteros o no se leen."""
        cambios = [f"REG-{i:03d}: estat_vigencia: vigent -> no_vigent" for i in range(40)]
        informe = self._informe(cambios_de_estado=cambios)

        texto = resumen("normatiu", "cb", informe)

        assert texto.count("estat_vigencia") == 40
        assert "y 28 mas" not in texto

    def test_should_separate_what_is_embedded_from_what_is_copied(self):
        informe = self._informe(
            ingeridos=1,
            copiados=2,
            detalle=["+ a.md", "≈ b.md (copiado de un gemelo)",
                     "≈ c.md (copiado de un gemelo)"],
        )

        texto = resumen("gerencia", "cb", informe)

        assert "NUEVOS, se embeben (1)" in texto
        assert "NUEVOS, se copian de un gemelo (2)" in texto

    def test_should_summarise_a_long_list_of_new_documents(self):
        informe = self._informe(detalle=[f"+ doc-{i}.md" for i in range(20)])

        texto = resumen("normatiu", "cb", informe)

        assert "NUEVOS, se embeben (20)" in texto
        assert "y 8 mas" in texto
