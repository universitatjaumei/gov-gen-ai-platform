"""USR.11 — el contrato de citas aguanta un contenido en bloques.

**Por qué existe este test.** USR.8 arregló los ocho sitios que leían el `content` del modelo a
pelo, y de paso enseñó que el problema no es de un sitio sino de la **frontera con el proveedor**:
Gemini devuelve el contenido como lista de bloques en cuanto la respuesta tiene más de una parte,
y quien lo asume `str` no falla al recibirlo —falla más tarde y en otro sitio—.

`enforce_citation_contract` es el último sitio del camino de la respuesta donde eso sigue
pudiendo pasar, y se comporta de **dos maneras distintas** según haya fuentes o no, que es lo peor
de los dos mundos. Medido el 2026-09-03:

* con `sources` reales → `TypeError: expected string or bytes-like object, got 'list'`, dentro del
  grafo. Ruidoso, y el cliente recibe `error`.
* con `sources` vacías → **devuelve la lista tal cual**, porque sale por `if not sources` antes de
  tocar una sola expresión regular. Su firma dice `-> str` y no lo cumple, así que una lista sigue
  viajando aguas abajo con la etiqueta de texto.

La segunda mitad es la que no avisa, y es la forma que llega al modo agéntico cuando el modelo
contesta sin leer nada (un saludo, una charla): ahí `sources` está vacío a propósito.

**Se normaliza en la entrada, no se envuelve en un `except`.** La diferencia importa: un `except`
convertiría un fallo en silencio —que es justo lo que se acaba de arreglar en dos sitios—,
mientras que normalizar con `texto_de` hace que la función cumpla su propia firma. El saber de
cómo se lee un `content` vive en un módulo, y éste es un llamador más.
"""
from __future__ import annotations

import uuid

from server.app.modules.agents_hub.services.retrieval.types import Source

URL = "https://normativa.uji.es/html/norma.html#art-63"

#: Lo que devuelve el proveedor cuando la respuesta tiene más de una parte.
BLOQUES = [
    {"type": "text", "text": "El límit dels contractes menors de serveis és de 15.000 euros "},
    {"type": "text", "text": f"[art. 63]({URL})"},
]


def _fuente(url: str = URL) -> Source:
    return Source(
        document_id=uuid.uuid4(),
        title="Normativa de contractació",
        url=url,
        excerpt="text",
        score=1.0,
    )


class TestConFuentes:
    """El caso que hoy levanta `TypeError` dentro del grafo."""

    def test_should_enforce_the_contract_on_block_content(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        resultado = enforce_citation_contract(
            BLOQUES, [_fuente()], "RAG", no_answer_message="no ho sé"
        )

        assert isinstance(resultado, str), f"la firma dice `-> str`: {type(resultado)}"
        # La cita es válida, así que la respuesta sobrevive: el contrato se ha **aplicado**,
        # no esquivado.
        assert URL in resultado
        assert "15.000 euros" in resultado

    def test_should_still_refuse_block_content_without_a_valid_citation(self):
        """Normalizar no puede convertirse en relajar: sin cita válida, sigue rindiéndose."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        sin_cita = [{"type": "text", "text": "El límit és de 15.000 euros."}]

        resultado = enforce_citation_contract(
            sin_cita, [_fuente()], "RAG", no_answer_message="no ho sé"
        )

        assert resultado == "no ho sé"


class TestSinFuentes:
    """El caso que no avisa: sale antes de mirar nada y devuelve la lista."""

    def test_should_return_text_and_not_the_raw_blocks(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        resultado = enforce_citation_contract(BLOQUES, [], "MD_AGENT_SELECTOR")

        assert isinstance(resultado, str), (
            "con `sources` vacías la función salía por la primera línea y devolvía la lista "
            f"del proveedor con la etiqueta de texto: {type(resultado)}"
        )
        assert "15.000 euros" in resultado


class TestLoQueYaFuncionabaSigueIgual:
    """`texto_de` de una cadena es la cadena: el camino de RAG no cambia."""

    def test_should_not_change_a_plain_string_answer(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = f"El límit és de 15.000 euros [art. 63]({URL})"

        assert (
            enforce_citation_contract(texto, [_fuente()], "RAG", no_answer_message="no ho sé")
            == texto
        )

    def test_should_not_change_the_surrender_of_a_plain_string_answer(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        assert (
            enforce_citation_contract(
                "El límit és de 15.000 euros.", [_fuente()], "RAG", no_answer_message="no ho sé"
            )
            == "no ho sé"
        )
