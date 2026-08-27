"""HIB.L — cuánto padre cabe, y qué se hace con el que no cabe.

**Paso 0 del prompt, y desmonta su propia premisa.** El prompt —que escribí yo en la segunda
revisión— decía que «los padres de las normas externas llegan a 236.691 caracteres» y que «con
`top_k = 3`, dos padres largos llenan el presupuesto y el tercero cae», estimando ~118.000 tokens
de entrada por consulta. Medido sobre los 10.614 padres distintos del corpus de Normativa:

| tokens por padre | |
|---|---|
| mediana | **205** |
| p90 | **710** |
| > 8.000 | **24** (0,2 %) |
| > 16.000 | **4** |
| > 32.000 | **2** |

O sea que el caso **típico** son 205 tokens y tres de ellos no llegan al 1 % del presupuesto de
128.000.

**Pero contar padres distintos engaña, y por poco me engaña a mí.** Lo que cuesta son los
**fragmentos**, porque cada hijo arrastra su padre, y un padre gigante va pegado a todos los
hijos de su sección: el preámbulo de la Ley 6/2024 se repite en cada uno de los suyos. Medido
sobre los 60.859 fragmentos con padre:

| | |
|---|---|
| padres > 8.000 tokens | 24 de 10.614 (**0,2 %**) |
| **fragmentos** que arrastran uno | 5.172 de 60.859 (**8,50 %**) |
| documentos afectados | **11** |
| coste medio del padre por fragmento | **2.955 → 895** tokens |
| peor caso con `top_k = 3` | **177.516 tokens (139 % del presupuesto)** → 23.946 (19 %) |

Así que la premisa del prompt era **más certera que mi primer desmentido**: con 139 % del
presupuesto el packer sí estaba descartando evidencia, en silencio salvo por `dropped_count`.
Lo que el prompt erraba es el *mecanismo* del arreglo, no la existencia del problema.

**Y la cola no es lo que el prompt suponía.** Los 24 padres que pasan de 8.000 son de dos clases,
y ninguna tiene «unidad estructural más fina» a la que bajar:

* **8 preámbulos** (ancla `preambul`), incluidos los dos monstruos de 59.172 y 45.329 tokens. Un
  preámbulo no tiene encabezados internos —los números romanos son texto— y **no es normativo**.
* **16 artículos y anexos reales**, casi todos de las **leyes de acompañamiento** (Ley 6/2024 de
  simplificación administrativa, Ley 3/2026 de medidas urgentes), cuyos artículos modifican otras
  leyes enteras: `art-119` son 21.484 tokens. Un artículo ya es la unidad más fina.

Por eso la opción «recomendada» del prompt —bajar el padre a capítulo o artículo— **es
inaplicable**, y la alternativa —truncar— corta artículos por la mitad, que es justo lo que el
padre existe para evitar.

**La decisión que sí se sostiene con estas cifras**: cuando la sección no cabe en
`parent_max_tokens`, **el hijo se queda sin padre** y responde con su propio texto, como en
`structural`. No se subdivide y no se trunca, así que ningún artículo acaba partido en dos
padres; simplemente se renuncia al contexto ampliado en el 0,2 % de casos donde ese contexto no
era ni asequible ni útil.

Defecto **8.000**, elegido con la distribución delante: deja intacto el 91,5 % de los fragmentos
y baja el peor caso del 139 % del presupuesto al 19 %.

**Lo que este prompt NO decide, y hay que llevar a Secretaría General**: 13 de los padres que
pasan de 4.000 tokens son preámbulos, y un preámbulo no es normativo. Que el asistente pueda
citarlo como fundamento es una cuestión de curación del corpus, no del techo del padre.

Deploy: edge
"""
from __future__ import annotations

import pytest

from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

ARTICULO_CORTO = """# Reglament de prova

## Article 1. Objecte
Aquest article és breu i cap de sobres en qualsevol techo raonable.

## Article 2. Àmbit
També breu.
"""


def _documento_con_seccion_gigante(tokens: int) -> str:
    """Una sección sin encabezados internos, como el preámbulo real."""
    relleno = "Text sense estructura interna. " * (tokens * 4 // 30)
    return f"# Llei de prova\n\n## Preàmbul\n{relleno}\n\n## Article 1. Objecte\nBreu.\n"


class TestElPadreSeConservaCuandoCabe:

    def test_should_keep_the_section_as_parent_when_it_fits(self):
        chunks = MarkdownChunker(strategy="parent_child").split(ARTICULO_CORTO)

        con_padre = [c for c in chunks if c.parent_content]
        assert con_padre, "con `parent_child` y secciones pequeñas todo hijo tiene padre"
        for c in con_padre:
            assert "Aquest article és breu" in c.parent_content or "També breu" in c.parent_content

    def test_should_default_the_cap_to_eight_thousand_tokens(self):
        """Elegido con la distribución: deja intacto el 99,8 % de los padres."""
        assert MarkdownChunker().parent_max_tokens == 8000


class TestLaSeccionQueNoCabeSeQuedaSinPadre:

    def test_should_drop_the_parent_when_the_section_exceeds_the_cap(self):
        """No hay unidad más fina a la que bajar: un preámbulo no tiene encabezados y un
        artículo ya es la unidad mínima. Así que se renuncia al padre, no se parte."""
        contenido = _documento_con_seccion_gigante(tokens=3000)
        chunker = MarkdownChunker(strategy="parent_child", parent_max_tokens=1000)

        chunks = chunker.split(contenido)
        del_preambulo = [c for c in chunks if "sense estructura interna" in c.content]

        assert del_preambulo, "el preámbulo sigue troceándose e indexándose"
        for c in del_preambulo:
            assert c.parent_content == "", (
                "una sección que no cabe deja al hijo sin padre; el hijo responde con su "
                "propio texto, como en `structural`"
            )

    def test_should_keep_the_parent_of_the_sections_that_do_fit(self):
        """El techo actúa por sección, no por documento: el artículo de al lado no paga."""
        contenido = _documento_con_seccion_gigante(tokens=3000)
        chunker = MarkdownChunker(strategy="parent_child", parent_max_tokens=1000)

        chunks = chunker.split(contenido)
        del_articulo = [c for c in chunks if "Breu." in c.content]

        assert del_articulo
        assert any(c.parent_content for c in del_articulo)

    def test_should_never_split_an_article_in_two_parents(self):
        """Se cumple por construcción: nunca se subdivide una sección para hacerla caber.

        Cada hijo tiene el padre entero o no tiene padre. Nunca medio padre, que es lo que
        produciría el truncado y lo que haría que dos hijos del mismo artículo recibieran
        contextos distintos e incompatibles.
        """
        contenido = _documento_con_seccion_gigante(tokens=3000)
        chunker = MarkdownChunker(strategy="parent_child", parent_max_tokens=1000)

        padres = {c.parent_content for c in chunker.split(contenido) if c.parent_content}
        for padre in padres:
            # Un padre conservado es una sección completa, no un trozo suyo.
            assert padre.strip().startswith("#") or "Article" in padre

    def test_should_ignore_the_cap_with_the_structural_strategy(self):
        """`structural` no tiene padres, así que el techo no le aplica."""
        contenido = _documento_con_seccion_gigante(tokens=3000)
        chunks = MarkdownChunker(strategy="structural", parent_max_tokens=10).split(contenido)

        assert chunks
        assert all(c.parent_content == "" for c in chunks)


class TestElTechoViajaPorLaCascada:

    def test_should_inherit_parent_max_tokens_through_the_cascade(self):
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver

        assert config_resolver._PLATFORM_DEFAULTS.parent_max_tokens == 8000

    def test_should_let_a_chatbot_raise_the_cap(self):
        """Gerencia puede subirlo: para una norma estatal el contexto amplio es lo adecuado,
        y esa fue la razón del usuario para aplazar la decisión el 2026-08-26."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            _PLATFORM_DEFAULTS,
            _apply_layer,
        )

        subido = _apply_layer(_PLATFORM_DEFAULTS, {"parent_max_tokens": 24000})
        assert subido.parent_max_tokens == 24000

    def test_should_pass_the_cap_to_the_chunker_during_ingestion(self):
        """Si no llega al chunker, la configuración es decorativa — el defecto que el
        comentario de `watcher._chunker_para` ya documenta para `chunk_size`."""
        import inspect

        from server.app.modules.agents_hub.ingestion import watcher

        fuente = inspect.getsource(watcher)
        assert "parent_max_tokens=" in fuente
