"""DER.2 — deriva entre copias de la misma norma.

Se descartó COR, así que la misma norma en dos asistentes son dos filas. Eso conserva que
cada asistente elija su modelo de embedding, y cuesta una cosa: que alguien recargue uno y no
el otro, y las dos copias queden con contenidos distintos sin que nada avise.

**La clave de identidad es `canonical_url`, no `content_hash`.** Hash igual significa
contenido idéntico; dos copias que han derivado tienen hashes **distintos**, así que agrupar
por hash es justo lo que no encuentra la deriva.

Deploy: edge
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

AYER = datetime(2026, 8, 10, tzinfo=timezone.utc)
HOY = AYER + timedelta(days=1)

URL = "https://www.uji.es/normativa/instruccio-1-2019"


def _copia(chatbot_id, content_hash, actualizado, **kw):
    from server.app.modules.agents_hub.ingestion.divergence_detector import CopiaDeDocumento

    return CopiaDeDocumento(
        document_id=kw.get("document_id", uuid.uuid4()),
        chatbot_id=chatbot_id,
        canonical_url=kw.get("canonical_url", URL),
        content_hash=content_hash,
        updated_at=actualizado,
        title=kw.get("title", "Instrucció 1/2019"),
        id_publicacio=kw.get("id_publicacio", "UJI-GER-2019-1"),
        estat_vigencia=kw.get("estat_vigencia", "vigent"),
    )


class TestQueCuentaComoDeriva:

    def test_should_not_flag_identical_copies(self):
        """Dos asistentes con la misma versión es el caso normal, no un hallazgo."""
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        a, b = uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [_copia(a, "hash-1", HOY), _copia(b, "hash-1", HOY)]
        )

        assert divergencias == []

    def test_should_not_flag_a_norm_present_in_a_single_chatbot(self):
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        assert agrupar_divergencias([_copia(uuid.uuid4(), "hash-1", HOY)]) == []

    def test_should_not_group_different_norms_together(self):
        """Se agrupa por `canonical_url`: dos normas distintas no son una deriva."""
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        a, b = uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [
                _copia(a, "hash-1", HOY, canonical_url="https://uji.es/a"),
                _copia(b, "hash-2", HOY, canonical_url="https://uji.es/b"),
            ]
        )

        assert divergencias == []

    def test_should_flag_the_same_norm_with_different_content(self):
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        viejo, nuevo = uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [_copia(viejo, "hash-viejo", AYER), _copia(nuevo, "hash-nuevo", HOY)]
        )

        assert len(divergencias) == 1
        assert divergencias[0].canonical_url == URL


class TestAQuienSeLeAvisa:

    def test_should_flag_the_chatbot_holding_the_older_copy(self):
        """El hallazgo cuelga de quien tiene que recargar, no de quien ya está al día.

        Si colgara del que está bien, la cola de revisión diría «revisa este asistente» a
        quien no tiene nada que hacer, y el que va atrasado no aparecería.
        """
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        viejo, nuevo = uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [_copia(viejo, "hash-viejo", AYER), _copia(nuevo, "hash-nuevo", HOY)]
        )

        assert [d.chatbot_id for d in divergencias] == [viejo]
        assert divergencias[0].senal()["hash_vigent"] == "hash-nuevo"

    def test_should_flag_every_stale_chatbot(self):
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        v1, v2, nuevo = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [
                _copia(v1, "hash-a", AYER),
                _copia(v2, "hash-b", AYER),
                _copia(nuevo, "hash-nuevo", HOY),
            ]
        )

        assert {d.chatbot_id for d in divergencias} == {v1, v2}

    def test_should_flag_all_of_them_when_it_cannot_tell_which_is_current(self):
        """Misma fecha y distinto contenido: no se puede saber cuál manda.

        Elegir una al azar sería peor que no decir nada, porque el aviso llevaría implícita
        una afirmación falsa. Se avisa a todos y se dice que es indeterminado.
        """
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        a, b = uuid.uuid4(), uuid.uuid4()
        divergencias = agrupar_divergencias(
            [_copia(a, "hash-a", HOY), _copia(b, "hash-b", HOY)]
        )

        assert {d.chatbot_id for d in divergencias} == {a, b}
        assert all(d.senal()["indeterminat"] for d in divergencias)


class TestLaGravedad:

    def test_should_be_a_warning_when_only_the_text_differs(self):
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        divergencias = agrupar_divergencias(
            [
                _copia(uuid.uuid4(), "hash-viejo", AYER),
                _copia(uuid.uuid4(), "hash-nuevo", HOY),
            ]
        )

        assert divergencias[0].severity == "warning"

    def test_should_be_critical_when_the_copies_disagree_on_whether_it_is_in_force(self):
        """Una copia dice «vigent» y otra «derogat».

        Es el peor caso posible en un asistente normativo: no es que una respuesta esté
        desactualizada, es que dos asistentes de la misma casa contestan lo contrario sobre
        si una norma está en vigor.
        """
        from server.app.modules.agents_hub.ingestion.divergence_detector import agrupar_divergencias

        divergencias = agrupar_divergencias(
            [
                _copia(uuid.uuid4(), "hash-viejo", AYER, estat_vigencia="vigent"),
                _copia(uuid.uuid4(), "hash-nuevo", HOY, estat_vigencia="derogat"),
            ]
        )

        assert divergencias[0].severity == "critical"


class TestElTipoDeHallazgoEstaEnElContrato:

    def test_should_be_a_declared_finding_type(self):
        """Sin declararlo, la pantalla de hallazgos no sabe qué está mirando."""
        from typing import get_args

        from server.app.modules.curation.contracts import FindingType
        from server.app.modules.agents_hub.ingestion.divergence_detector import TIPO

        assert TIPO in get_args(FindingType)


class TestLaPersistencia:

    @pytest.mark.asyncio
    async def test_should_not_duplicate_an_open_finding_on_each_run(self):
        """El detector corre periódicamente; sin deduplicar, la cola es inservible en una
        semana. Mismo criterio que `staleness_detector` y por el mismo motivo."""
        from unittest.mock import AsyncMock, MagicMock

        from server.app.modules.agents_hub.ingestion.divergence_detector import (
            TIPO,
            analizar_divergencias,
        )

        viejo, nuevo = uuid.uuid4(), uuid.uuid4()
        copias = [_copia(viejo, "hash-viejo", AYER), _copia(nuevo, "hash-nuevo", HOY)]

        abierto = MagicMock()
        abierto.chatbot_id = viejo
        abierto.finding_type = TIPO
        abierto.status = "new"
        abierto.signal_json = {"canonical_url": URL}

        session = AsyncMock()
        resultado_copias = MagicMock()
        resultado_copias.all.return_value = [
            (c.document_id, c.chatbot_id, c.canonical_url, c.content_hash,
             c.updated_at, c.title, c.id_publicacio, c.estat_vigencia)
            for c in copias
        ]
        resultado_abiertos = MagicMock()
        resultado_abiertos.scalars.return_value.all.return_value = [abierto]
        session.execute = AsyncMock(side_effect=[resultado_copias, resultado_abiertos])

        n = await analizar_divergencias(session, [viejo, nuevo])

        assert n == 1
        session.add.assert_not_called()
        assert abierto.signal_json["hash_vigent"] == "hash-nuevo"
