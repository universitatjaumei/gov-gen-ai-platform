"""Lo que el MCP expone y lo que la documentación dice que expone son lo mismo (issue #89).

**El fallo.** El documento de despliegue decía que el cliente «obtiene **tres** herramientas». El
servidor expone **siete**: se quedó congelado en REG.4 y no incorporó las cuatro del bloque VAS.

Y lo grave no era la cifra suelta, sino dónde estaba la segunda: *«Un `200` con **las tres
herramientas** en el cuerpo es la señal buena»* — **un criterio de aceptación equivocado**. Quien
siguiera el documento para comprobar un despliegue vería siete y no sabría si estaba bien.

El tercer sitio era el peor de los tres: el docstring del propio `http_server.py` decía «estas
tres tools», así que **ni leyendo el código se salía del error**.

**Por qué esto es un test y no una corrección.** Corregir «tres» por «siete» deja el mismo fallo
esperando al siguiente bloque que añada un juego de herramientas. Lo que no puede volver a pasar
es que la cifra se escriba a mano en un sitio y el servidor diga otra cosa, así que aquí se cruza
la lista **de verdad registrada** con lo que la documentación nombra.

**Se leen los nombres, no se cuentan.** Un test que comparase cantidades pasaría en verde el día
que se retire una herramienta y se añada otra, que es justo cuando la documentación empieza a
mentir sobre cuáles.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MCP = RAIZ / "mcp_server"
DOC = RAIZ / "docs" / "DESPLIEGUE_PROTOTIPO_GCP.md"

#: `@mcp.tool()` seguido de la función que declara. El nombre de la función **es** el de la
#: herramienta: así lo registra FastMCP.
_HERRAMIENTA = re.compile(r"@mcp\.tool\(\)\s*\n\s*async def (\w+)")

#: Las funciones de registro que **el servidor HTTP** llama.
_REGISTRO = re.compile(r"\b(register_\w+_tools)\(")


def _modulos_del_servidor_http() -> list[Path]:
    """Sólo los que registra `http_server`, y no todo `tools/`.

    La primera versión leía `tools/*.py` entero y salían **23** herramientas en vez de 7: ahí
    viven también las del servidor **stdio** —`create_chatbot`, `list_chatbots`…— que el
    servidor HTTP no monta. Un guardarraíl que exigiera documentarlas todas habría obligado a
    escribir en el documento de despliegue cosas que ese despliegue no expone.
    """
    llamadas = set(_REGISTRO.findall((MCP / "http_server.py").read_text(encoding="utf-8")))
    modulos = []
    for fichero in sorted((MCP / "tools").glob("*.py")):
        texto = fichero.read_text(encoding="utf-8")
        if any(f"def {nombre}(" in texto for nombre in llamadas):
            modulos.append(fichero)
    return modulos


def herramientas_registradas() -> set[str]:
    nombres: set[str] = set()
    for modulo in _modulos_del_servidor_http():
        nombres.update(_HERRAMIENTA.findall(modulo.read_text(encoding="utf-8")))
    return nombres


def test_el_medidor_encuentra_las_herramientas() -> None:
    """Un guardarraíl que no encuentra ninguna pasaría en verde sin comprobar nada."""
    modulos = _modulos_del_servidor_http()
    assert modulos, "no encuentro qué módulos registra `http_server`"
    encontradas = herramientas_registradas()
    assert len(encontradas) >= 5, (
        f"sólo veo {sorted(encontradas)} en {[m.name for m in modulos]}: el patrón ya no casa "
        "con cómo se registran, y este fichero habría dejado de vigilar sin avisar"
    )


def test_la_documentacion_las_nombra_todas() -> None:
    """Y por nombre, no por cantidad."""
    texto = DOC.read_text(encoding="utf-8")
    faltan = sorted(h for h in herramientas_registradas() if h not in texto)
    assert faltan == [], (
        f"el MCP registra herramientas que `{DOC.name}` no nombra: {faltan}.\n\n"
        "El documento es la referencia para comprobar un despliegue; si no las nombra, quien lo "
        "siga no sabe qué debería ver."
    )


def test_la_documentacion_no_escribe_la_cifra_a_mano() -> None:
    """Porque una cifra escrita se congela, y ésta ya se congeló una vez en «tres»."""
    texto = DOC.read_text(encoding="utf-8")
    cifras = re.findall(
        r"\b(tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+herramientas\b",
        texto,
        re.IGNORECASE,
    )
    assert cifras == [], (
        f"`{DOC.name}` escribe la cantidad de herramientas a mano: {cifras}. Se congela en el "
        "siguiente bloque que añada un juego, que es exactamente lo que pasó con «tres» cuando "
        "VAS añadió cuatro. Nómbralas o remite a lo que registre `http_server`."
    )


def test_el_docstring_del_servidor_tampoco_la_escribe() -> None:
    """Era el tercer sitio, y el que más engañaba: estaba **en el código**."""
    texto = (MCP / "http_server.py").read_text(encoding="utf-8")
    cifras = re.findall(
        r"\b(tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+tools?\b", texto, re.IGNORECASE
    )
    assert cifras == [], (
        f"`http_server.py` describe sus herramientas por cantidad: {cifras}. El módulo que "
        "registra siete se describía como si tuviera tres, así que ni leyendo el código se "
        "salía del error."
    )
