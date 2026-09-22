"""La versión es una sola, y un sistema en marcha puede decir cuál ejecuta.

**El hueco.** Antes de esto el proyecto no tenía versión: cero etiquetas, cero *releases*, y
cuatro manifiestos que ya discrepaban —`0.1.0` en tres y `0.0.0` en el frontend— sin que nada los
cruzara. `/api/v1/instancia` publicaba el enlace al código fuente del §13 de la AGPL y nada más,
así que **a un despliegue en marcha no se le podía preguntar qué es**.

Eso importa en cuanto alguien que no somos nosotros lo instala: sin número no puede decir en qué
está, ni nosotros preguntárselo, y «funciona» o «falla» dejan de ser afirmaciones comprobables.

**Por qué en `instancia` y no en `/health`.** `/health` es una sonda de vida: responde `healthy` y
lo consume un supervisor que sólo mira el código de estado. `instancia` ya existe declarando ser
«metadatos públicos de este despliegue», público y sin credencial a propósito. La versión es
exactamente eso, así que va donde ya está su sitio en vez de abrir uno nuevo.

**Y por qué un fichero `VERSION` y no el `pyproject.toml` del servidor.** Porque lo que se versiona
no es un paquete de Python: es **el despliegue**, que son cuatro imágenes más la cabeza de Alembic.
Ninguno de los cuatro manifiestos es más «el proyecto» que los otros, y elegir uno dejaría a los
otros tres divergiendo en silencio, que es como llegaron a `0.1.0` y `0.0.0`.

Este fichero es el que impide que `VERSION` se convierta en un quinto sitio que dice otra cosa.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FICHERO_VERSION = RAIZ / "VERSION"
DEPLOY = RAIZ / ".github" / "workflows" / "deploy.yml"
DOCKERFILE = RAIZ / "Dockerfile"

#: `0.x` a propósito: en semver significa «cualquier cosa puede romperse», que es lo que un
#: proyecto experimental tiene que comunicar. Subir a `1.0.0` diría lo contrario —compatibilidad
#: comprometida— y este proyecto **no presta soporte** (README, «Qué no acompaña a la publicación»).
_FORMATO = re.compile(r"^0\.\d+\.\d+$")

_MANIFIESTOS_PYTHON = (
    "server/pyproject.toml",
    "mcp_server/pyproject.toml",
    "services/script_sandbox/pyproject.toml",
)


def _version_declarada() -> str:
    assert FICHERO_VERSION.is_file(), (
        "no existe el fichero `VERSION` en la raíz. Es la fuente única: sin él cada manifiesto "
        "vuelve a decir lo suyo."
    )
    return FICHERO_VERSION.read_text(encoding="utf-8").strip()


class TestLaVersionEsUnaSola:
    def test_el_fichero_version_existe_y_tiene_forma_de_version(self) -> None:
        version = _version_declarada()
        assert _FORMATO.match(version), (
            f"`VERSION` dice «{version}» y se espera `0.MENOR.PARCHE`. El `0.` no sube: es la "
            "declaración de que el proyecto es experimental, y está razonado en "
            "`docs/VERSIONADO.md`."
        )

    def test_los_manifiestos_de_python_dicen_lo_mismo(self) -> None:
        version = _version_declarada()
        discrepan: list[str] = []
        for rel in _MANIFIESTOS_PYTHON:
            texto = (RAIZ / rel).read_text(encoding="utf-8")
            encontrada = re.search(r'^version\s*=\s*"([^"]+)"', texto, re.MULTILINE)
            assert encontrada, f"{rel} no declara `version`"
            if encontrada.group(1) != version:
                discrepan.append(f"{rel} dice «{encontrada.group(1)}»")
        assert discrepan == [], (
            f"`VERSION` dice «{version}» y no coinciden:\n  " + "\n  ".join(discrepan)
        )

    def test_el_manifiesto_del_frontend_dice_lo_mismo(self) -> None:
        version = _version_declarada()
        paquete = json.loads((RAIZ / "frontend" / "package.json").read_text(encoding="utf-8"))
        assert paquete.get("version") == version, (
            f"`frontend/package.json` dice «{paquete.get('version')}» y `VERSION` dice "
            f"«{version}». Es el que más lejos estaba: nació en `0.0.0` y ahí se quedó."
        )


class TestSeLePuedePreguntarAUnDespliegue:
    def test_instancia_publica_la_version(self) -> None:
        """El endpoint la devuelve, y es lo que hace útil numerar."""
        from fastapi.testclient import TestClient

        from server.app.main import app

        cliente = TestClient(app, raise_server_exceptions=False)
        cuerpo = cliente.get("/api/v1/instancia").json()

        assert "version" in cuerpo, (
            "`/api/v1/instancia` no publica la versión. Sin esto no se le puede preguntar a un "
            "despliegue qué ejecuta, que es todo el motivo de numerar."
        )
        assert cuerpo["version"] == _version_declarada()

    def test_la_version_no_desaparece_si_falta_la_variable(self, monkeypatch) -> None:
        """En la imagen llega por variable; en desarrollo, del fichero. Nunca vacía.

        Una versión que a veces es `None` obliga a quien la lee a tratar el caso, y acaba
        mostrándose en blanco justo cuando hace falta: al reportar un fallo.

        **El `cache_clear()` no es higiene, es lo que hace que esto pruebe algo.** `version()`
        está cacheada con `lru_cache`, así que sin vaciarla devuelve lo que se resolvió en la
        primera llamada del proceso —otro test de este mismo fichero la llama antes— y el
        camino del fichero no se ejercita. Medido: fijando la variable a un valor inventado,
        borrándola y volviendo a llamar, **seguía devolviendo el inventado**.

        Da la casualidad de que aquí los dos caminos responden lo mismo, así que el test pasaba
        igual. Un verde por casualidad, que es la peor clase.
        """
        from server.app.core import version as modulo

        monkeypatch.delenv("GOVGENAI_VERSION", raising=False)
        modulo.version.cache_clear()
        try:
            assert modulo.version() == _version_declarada()
        finally:
            # Y se vacía también al salir: si no, el valor resuelto sin variable se quedaría
            # cacheado para los tests que corran después en este mismo proceso.
            modulo.version.cache_clear()

    def test_la_variable_de_la_imagen_gana_al_fichero(self, monkeypatch) -> None:
        """El otro camino, que sin esto no lo probaba nadie.

        Es el que usa producción: la versión va estampada en la imagen. Si el fichero ganara,
        una imagen diría la versión del árbol de quien la construyó y no la suya.
        """
        from server.app.core import version as modulo

        monkeypatch.setenv("GOVGENAI_VERSION", "9.9.9+de-la-imagen")
        modulo.version.cache_clear()
        try:
            assert modulo.version() == "9.9.9+de-la-imagen"
        finally:
            modulo.version.cache_clear()


class TestLaImagenLlevaLaVersionEstampada:
    """Tres sitios que tienen que decir lo mismo, y sin esto nada los cruza.

    Es el mismo fallo que dejó el login con Google apagado en producción: la variable estaba
    declarada y escrita, y no llegaba al contenedor porque un tramo del cableado no la nombraba.
    """

    def test_el_dockerfile_declara_el_argumento_y_lo_fija(self) -> None:
        texto = DOCKERFILE.read_text(encoding="utf-8")
        assert "ARG GOVGENAI_VERSION" in texto, (
            "el `Dockerfile` no declara `ARG GOVGENAI_VERSION`: la imagen se construiría sin saber "
            "qué versión es"
        )
        assert "ENV GOVGENAI_VERSION" in texto, (
            "declara el ARG pero no lo fija como ENV, así que el valor se pierde al arrancar: un "
            "ARG sólo vive durante la construcción"
        )

    def test_el_despliegue_pasa_la_version_al_construir(self) -> None:
        texto = DEPLOY.read_text(encoding="utf-8")
        assert "GOVGENAI_VERSION=" in texto, (
            "`deploy.yml` no pasa `--build-arg GOVGENAI_VERSION=...`, así que la imagen de "
            "producción se construiría con el valor por defecto y mentiría sobre su versión"
        )
