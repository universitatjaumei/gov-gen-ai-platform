"""HIB.T — selección vectorial por top-k con inyección del documento ENTERO.

**De dónde sale.** El experimento de granularidad midió siete formas de decidir qué texto darle
al modelo, y la de **cinco normas enteras elegidas por el top-k vectorial** fue la única que ganó
a Gemini de forma significativa (7 a 0, p=0,016) y quedó segunda de las siete (68 %). Pero se
midió **con una llamada directa al modelo**, así que no llevaba contrato de citas, ni ancla, ni
aviso de vigencia: **0 enlaces de 25**. Tal como se midió no era desplegable.

**Y el modo que ya existía no sirve.** `MD_LONG_CONTEXT` selecciona por **fecha de creación**
hasta llenar el presupuesto e **ignora la consulta**: para un corpus con leyes estatales de
279.425 tokens, eso es arbitrario.

Lo que falta no es una estrategia nueva: es **un mando en la que ya hay**. `VectorRetrievalStrategy`
ya elige por relevancia, agrupa por documento, construye la URL de cita con su ancla, hidrata el
aviso de desplazamiento y recorta a `top_k` documentos. Lo único que cambia es **qué texto pone en
el `excerpt`**: el artículo (el padre del fragmento) o el documento entero.

Hacerlo así es lo que garantiza que la inyección herede las cuatro cosas que a las celdas del
experimento les faltaban. Una estrategia nueva las habría vuelto a dejar fuera.
"""
import uuid

import pytest

from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
    VectorRetrievalStrategy,
)


def test_should_default_to_injecting_the_article_and_not_the_whole_document():
    """El defecto no cambia: los tres asistentes en producción inyectan el artículo."""
    e = VectorRetrievalStrategy(session=None, embedding_service=None, top_k=3)
    assert e.inject_whole_document is False


def test_should_accept_the_whole_document_flag():
    e = VectorRetrievalStrategy(
        session=None, embedding_service=None, top_k=5, inject_whole_document=True
    )
    assert e.inject_whole_document is True


class _Doc:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.title = "Reglament de permanencia"
        self.canonical_url = "https://www.uji.es/permanencia"
        self.markdown_content = "TEXTO COMPLETO DE LA NORMA, todos sus articulos."
        self.estat_vigencia = "vigent"
        self.doc_metadata = {}
        self.vigencia_validada_el = None
        self.desplacat_per = None


class _Chunk:
    def __init__(self) -> None:
        self.content = "solo el fragmento hijo"
        self.parent_content = "Article 4. El articulo entero, que es el padre del fragmento."
        self.metadata = {"ancora": "art-4"}
        self.score = 0.8
        self.relevance = 0.74
        self.source_url = "https://www.uji.es/permanencia"


class TestQueTextoLlegaAlModelo:
    """El resto del contrato —ancla, URL de cita, vigencia, agrupación— no se toca: es
    exactamente lo que las celdas del experimento perdieron por vivir fuera del grafo."""

    def test_should_inject_the_article_when_the_flag_is_off(self):
        e = VectorRetrievalStrategy(session=None, embedding_service=None, top_k=3)
        assert e._texto_de_evidencia(_Chunk(), _Doc()) == (
            "Article 4. El articulo entero, que es el padre del fragmento."
        )

    def test_should_inject_the_whole_document_when_the_flag_is_on(self):
        e = VectorRetrievalStrategy(
            session=None, embedding_service=None, top_k=5, inject_whole_document=True
        )
        assert e._texto_de_evidencia(_Chunk(), _Doc()) == (
            "TEXTO COMPLETO DE LA NORMA, todos sus articulos."
        )

    def test_should_fall_back_to_the_article_when_there_is_no_document(self):
        """Un fragmento temporal o de legado no tiene documento del que sacar el texto entero.
        Sin esta salida, el `excerpt` saldría vacío y la respuesta se quedaría sin fundamento
        **sin dar ningún error**, que es el modo de fallo que este bloque lleva cazando."""
        e = VectorRetrievalStrategy(
            session=None, embedding_service=None, top_k=5, inject_whole_document=True
        )
        assert e._texto_de_evidencia(_Chunk(), None) == (
            "Article 4. El articulo entero, que es el padre del fragmento."
        )

    def test_should_fall_back_to_the_article_when_the_document_has_no_text(self):
        doc = _Doc()
        doc.markdown_content = ""
        e = VectorRetrievalStrategy(
            session=None, embedding_service=None, top_k=5, inject_whole_document=True
        )
        assert e._texto_de_evidencia(_Chunk(), doc) == (
            "Article 4. El articulo entero, que es el padre del fragmento."
        )

    def test_should_fall_back_to_the_child_when_there_is_no_parent_either(self):
        c = _Chunk()
        c.parent_content = ""
        e = VectorRetrievalStrategy(session=None, embedding_service=None, top_k=3)
        assert e._texto_de_evidencia(c, _Doc()) == "solo el fragmento hijo"
