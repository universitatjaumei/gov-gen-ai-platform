"""Tests TDD — Metadatos del corpus en HubDocument (Prompt ING.0.2).

Regla que decide el esquema: una columna de primer nivel SOLO si algo la filtra, la
ordena o la usa como puerta. Todo lo demás va a `doc_metadata` JSONB. Sin esta
disciplina, las 56 columnas del esquema de metadatos acabarían en la tabla.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import CheckConstraint, Index


def _make_document(**kwargs):
    from server.app.modules.agents_hub.database.operational_models import HubDocument

    defaults = dict(
        id=uuid.uuid4(),
        chatbot_id=uuid.uuid4(),
        title="Reglament de prova",
        canonical_url="https://www.uji.es/norma",
        markdown_content="# Reglament\n\n##### Article 1 {#art-1}\n\nText.",
        content_hash="a" * 64,
        language="ca",
        source_kind="publicacio",
    )
    defaults.update(kwargs)
    return HubDocument(**defaults)


# ───────────────────── Columnas de primer nivel ─────────────────────


class TestColumnasDeFiltro:

    @pytest.mark.parametrize(
        "columna",
        [
            "content_class",
            "ambit_principal",
            "ambits_secundaris",
            "submateries",
            "submateries_internes",
            "nivell_acces",
            "us_assistents",
            "canonica",
            "versio_idiomatica_de",
            "estat_vigencia",
            "vigencia_validada_el",
            "revisat_per",
            "revisat_el",
            "data_revisio_prevista",
            "id_publicacio",
            "last_seen_at",
            "doc_metadata",
        ],
    )
    def test_columna_existe(self, columna: str):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        assert columna in HubDocument.__table__.c, f"falta la columna {columna}"

    def test_should_default_new_document_to_public_and_canonical(self):
        doc = _make_document()
        # Los defaults del ORM se materializan al insertar; se comprueban en la columna.
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        cols = HubDocument.__table__.c
        assert cols["nivell_acces"].default.arg == "public"
        assert cols["us_assistents"].default.arg == "si"
        assert cols["canonica"].default.arg is True
        assert cols["content_class"].default.arg == "generic"
        assert doc.ambit_principal is None

    def test_arrays_son_nullable_false_con_default_lista(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        for name in ("ambits_secundaris", "submateries", "submateries_internes"):
            col = HubDocument.__table__.c[name]
            assert col.default is not None, f"{name} sin default"

    def test_no_hay_columna_origen_nueva(self):
        """El origen se expresa con source_kind, que ya existía. Duplicar el eje
        sería deuda: los valores documentados pasan a incluir publicacio y boe."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        assert "origen" not in HubDocument.__table__.c
        assert "source_kind" in HubDocument.__table__.c

    def test_source_kind_acepta_los_origenes_nuevos(self):
        for origen in ("crawler", "upload", "publicacio", "boe"):
            assert _make_document(source_kind=origen).source_kind == origen


# ───────────────────── Enumeraciones cerradas vs vocabulario ─────────────────────


class TestRestricciones:

    def _checks(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        return {
            c.name: str(c.sqltext)
            for c in HubDocument.__table__.constraints
            if isinstance(c, CheckConstraint)
        }

    @pytest.mark.parametrize(
        "campo", ["nivell_acces", "us_assistents", "content_class"]
    )
    def test_enumeraciones_cerradas_con_check(self, campo: str):
        """Estas SÍ son enumeraciones estables con consumidor (filtrado fail-closed):
        llevan CHECK, al contrario que los códigos de vocabulario."""
        assert any(campo in sql for sql in self._checks().values()), (
            f"{campo} deberia tener CheckConstraint"
        )

    @pytest.mark.parametrize(
        "campo", ["ambit_principal", "submateries", "estat_vigencia"]
    )
    def test_vocabulario_y_vigencia_sin_check(self, campo: str):
        """CLAUDE.md §5: los códigos de vocabulario son dato revisable, nunca CHECK.
        estat_vigencia tampoco: el catálogo real trae valores como 'vigent?'."""
        assert not any(campo in sql for sql in self._checks().values()), (
            f"{campo} no debe llevar CheckConstraint"
        )


# ───────────────────── Índices ─────────────────────


class TestIndices:

    def _indices(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        return {i.name: i for i in HubDocument.__table__.indexes}

    def test_should_have_gin_index_on_submateries(self):
        gin = [
            i for i in self._indices().values()
            if i.dialect_options.get("postgresql", {}).get("using") == "gin"
            and "submateries" in [c.name for c in i.columns]
        ]
        assert gin, "falta el indice GIN sobre submateries"

    def test_gin_index_on_submateries_internes_and_doc_metadata(self):
        gin_cols = {
            c.name
            for i in self._indices().values()
            if i.dialect_options.get("postgresql", {}).get("using") == "gin"
            for c in i.columns
        }
        assert {"submateries_internes", "doc_metadata"} <= gin_cols

    def test_composite_index_for_ambit_and_nivell_acces(self):
        combos = {
            tuple(c.name for c in i.columns) for i in self._indices().values()
        }
        assert ("chatbot_id", "ambit_principal") in combos
        assert ("chatbot_id", "nivell_acces") in combos

    def test_id_publicacio_indexada(self):
        """Es la clave de emparejamiento del sync (SYNC.1)."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        col = HubDocument.__table__.c["id_publicacio"]
        indexadas = {
            c.name for i in HubDocument.__table__.indexes for c in i.columns
        }
        assert col.index or "id_publicacio" in indexadas


# ───────────────────── FK que VIS.1 necesita ─────────────────────


class TestForeignKeyDeChunks:

    def test_document_id_tiene_fk_con_cascade(self):
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )

        col = HubDocumentChunk.__table__.c["document_id"]
        fks = list(col.foreign_keys)
        assert fks, "document_id sigue sin FK: VIS.1 necesita el JOIN"
        assert fks[0].column.table.name == "hub_documents"
        assert fks[0].ondelete == "CASCADE"

    def test_document_id_sigue_siendo_nullable(self):
        """Los chunks temporales de subida de usuario no tienen documento."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )

        assert HubDocumentChunk.__table__.c["document_id"].nullable is True


# ───────────────────── Columna muerta que se retira ─────────────────────


class TestColumnaMuerta:

    def test_hub_interactions_no_declara_metadata(self):
        """SQLAlchemy reserva `metadata` en las clases declarativas, que es por lo que
        el ORM usa interaction_metadata. La columna `metadata` que crea la migración
        a1b2c3d4e5f6 es inalcanzable: se retira en ING.0.2."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubInteraction,
        )

        assert "metadata" not in HubInteraction.__table__.c
        assert "interaction_metadata" in HubInteraction.__table__.c
