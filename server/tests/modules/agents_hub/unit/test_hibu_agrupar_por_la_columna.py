"""HIB.U — agrupar por la COLUMNA `document_id`, no por el metadato.

**El fallo que esto hace imposible, encontrado el 2026-08-28.** El asistente agéntico de Gerencia
tenía 14.198 de sus 14.208 fragmentos con `chunk_metadata["document_id"]` apuntando a documentos
del chatbot **RAG**. Los fragmentos eran suyos —la columna `chatbot_id` estaba bien, así que la
búsqueda los filtraba correctamente— pero `VectorRetrievalStrategy` agrupaba por el
`document_id` del **metadato**, así que cargaba las filas del hermano y **la cita salía con su
título**. Sin ningún error.

El arreglo de los datos fue un `UPDATE`. Este es el arreglo de la causa: la columna es la fuente
de verdad —la fija la base de datos con una clave ajena— y el metadato es una copia denormalizada
que se escribe al trocear. Cuando dos copias del mismo dato pueden discrepar, hay que leer la que
no se puede corromper sin que la base se queje.

El metadato se conserva como repliegue para los fragmentos legados, que se crearon cuando la
columna no existía. Ése es el motivo por el que la agrupación miraba el metadato: era el único que
había, y siguió mirándolo después.
"""
import uuid

from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
    documento_del_fragmento,
)


class _Fragmento:
    def __init__(self, columna, metadato) -> None:
        self.document_id = columna
        self.metadata = {"document_id": str(metadato)} if metadato else {}


class TestDeQuienEsElFragmento:

    def test_should_prefer_the_column_over_the_metadata(self):
        """El caso real: la columna apunta al documento propio y el metadato al del hermano."""
        propio, ajeno = uuid.uuid4(), uuid.uuid4()
        assert documento_del_fragmento(_Fragmento(propio, ajeno)) == propio

    def test_should_fall_back_to_the_metadata_for_legacy_chunks(self):
        """Los fragmentos legados se crearon sin la columna. Sin el repliegue dejarian de
        agruparse y cada uno saldria como un documento distinto."""
        del_metadato = uuid.uuid4()
        assert documento_del_fragmento(_Fragmento(None, del_metadato)) == del_metadato

    def test_should_return_none_when_neither_is_there(self):
        assert documento_del_fragmento(_Fragmento(None, None)) is None

    def test_should_accept_the_column_as_a_string(self):
        """El id llega como texto desde algunos caminos; agrupar por tipos distintos partiria
        en dos grupos los fragmentos del mismo documento."""
        propio = uuid.uuid4()
        assert documento_del_fragmento(_Fragmento(str(propio), None)) == propio

    def test_should_ignore_a_metadata_that_is_not_a_valid_id(self):
        f = _Fragmento(None, None)
        f.metadata = {"document_id": "no-es-un-uuid"}
        assert documento_del_fragmento(f) is None
