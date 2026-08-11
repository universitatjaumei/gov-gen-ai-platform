"""Los perfiles de grafo sin configurar fallan en alto (hallazgo I5 de la auditoría).

`PUBLIC_PORTAL_AGGREGATOR` y `PUBLIC_PORTAL_ROUTER` están **registrados como seleccionables**
en el registro de perfiles, pero sus factorías son stubs: el primero cablea
`uuid.UUID(int=0)` como identificador de los dos chatbots de los que agrega, y el segundo una
lista de hijos vacía.

El efecto no es un error: es **una respuesta vacía en silencio**. Quien configure un chatbot
con uno de estos perfiles verá que el asistente no encuentra nada y no tendrá forma de saber
por qué — no hay traza, no hay log, y el corpus está bien cargado. Es exactamente la avería
muda que este proyecto se ha encontrado ya tres veces.

Y toca ahora porque el siguiente paso es **configurar los dos chatbots del piloto**: el perfil
aparece en la lista, con un nombre que suena a lo que se quiere.

La corrección no es implementarlos —eso es una funcionalidad con su propio alcance— sino que
digan que no están configurados.
"""
from __future__ import annotations

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import (
    PERFILES_SIN_CONFIGURAR as _PERFILES_SIN_CONFIGURAR,
)


def _construir(perfil):
    from types import SimpleNamespace

    # El import registra los perfiles como efecto de carga del módulo.
    import server.app.modules.agents_hub.agent.public_graphs.core.graph_factory  # noqa: F401
    from server.app.modules.agents_hub.agent.public_graphs.registry import get_profile

    cfg = SimpleNamespace(public_graph_profile=perfil, retrieval_mode="MD_FULL")
    deps = SimpleNamespace(session=None, embedder=None, llm=None)
    return get_profile(perfil.value)(cfg, deps, None)


class TestLosPerfilesStubNoDevuelvenVacioEnSilencio:

    @pytest.mark.parametrize("perfil", sorted(_PERFILES_SIN_CONFIGURAR))
    def test_should_refuse_to_build_an_unconfigured_profile(self, perfil):
        from server.app.modules.agents_hub.agent.public_graphs.types import (
            PublicGraphProfile,
        )

        with pytest.raises(NotImplementedError):
            _construir(PublicGraphProfile(perfil))

    @pytest.mark.parametrize("perfil", sorted(_PERFILES_SIN_CONFIGURAR))
    def test_should_say_what_to_use_instead(self, perfil):
        """Quien está configurando un chatbot necesita saber qué elegir, no solo que esto
        no vale."""
        from server.app.modules.agents_hub.agent.public_graphs.types import (
            PublicGraphProfile,
        )

        with pytest.raises(NotImplementedError) as exc:
            _construir(PublicGraphProfile(perfil))

        mensaje = str(exc.value)
        assert "PUBLIC_KB_RICH" in mensaje, mensaje


class TestElPerfilQueSiFuncionaSigueFuncionando:

    def test_should_still_build_public_kb_rich(self):
        from server.app.modules.agents_hub.agent.public_graphs.types import (
            PublicGraphProfile,
        )

        grafo = _construir(PublicGraphProfile.PUBLIC_KB_RICH)

        assert grafo is not None
