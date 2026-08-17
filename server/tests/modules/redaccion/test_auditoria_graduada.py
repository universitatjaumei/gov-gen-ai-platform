"""PRO.1 — la auditoría determinista deja de ser binaria.

Hasta aquí `ScriptSecurityAuditor` ponía `approved = not findings`: un `import csv`
—un módulo que no está en la lista blanca y nada más— tumbaba la propuesta exactamente
igual que un `eval()`. Con eso el modelo escribe scripts razonables que nadie puede
aprobar, y el administrador no tiene forma de distinguir un problema de seguridad de un
hueco en una lista.

El legacy lo tenía resuelto en `AutomatIA/shared/automatia_shared/core/security.py`:
`audit_code()` devuelve `SAFE`/`WARNING`/`CRITICAL` con motivos, y **antes del AST**
comprueba por regex rutas absolutas de Windows y de sistema Linux. Esa comprobación no
existía aquí: un script que abriera `C:\\Users\\...` con pandas pasaba la auditoría.
"""
from __future__ import annotations

import pytest


def _auditar(codigo: str):
    from server.app.modules.redaccion.services.script_auditor import ScriptSecurityAuditor

    return ScriptSecurityAuditor().audit(codigo)


# ---------------------------------------------------------------------------
# Los tres niveles
# ---------------------------------------------------------------------------

class TestTresNiveles:
    def test_should_marcar_modulo_fuera_de_lista_blanca_como_warning_revisable(self) -> None:
        """`import csv` no es un problema de seguridad: es un hueco en una lista."""
        resultado = _auditar("import csv\nresult = {'tables': [], 'metrics': []}\n")

        assert resultado.risk_level == "WARNING"
        assert resultado.puede_revisarse is True, (
            "un módulo fuera de la lista blanca tiene que poder aceptarlo una persona"
        )
        assert resultado.approved is False, "`approved` sigue significando «sin hallazgos»"

    def test_should_marcar_eval_como_critico_y_no_revisable(self) -> None:
        resultado = _auditar("result = eval('1+1')\n")

        assert resultado.risk_level == "CRITICAL"
        assert resultado.puede_revisarse is False
        assert resultado.approved is False

    def test_should_dejar_en_safe_un_script_legitimo(self) -> None:
        codigo = (
            "import pandas as pd\n"
            "df = pd.read_excel(file_path)\n"
            "result = {'tables': [], 'metrics': [{'name': 'filas', 'value': len(df)}]}\n"
        )
        resultado = _auditar(codigo)

        assert resultado.risk_level == "SAFE", resultado.findings
        assert resultado.approved is True
        assert resultado.puede_revisarse is True

    def test_should_ganar_el_critico_cuando_hay_warning_y_critico(self) -> None:
        """Un warning no diluye un crítico: el nivel es el del peor hallazgo."""
        resultado = _auditar("import csv\nresult = eval('1+1')\n")

        assert resultado.risk_level == "CRITICAL"
        assert resultado.puede_revisarse is False


class TestDosListasNoUna:
    """El legacy tenía denegación explícita **y** denegación por defecto.

    Es la distinción que hace segura la graduación: si «fuera de la lista blanca» fuera
    siempre un warning revisable, un administrador podría aceptar `import os` mirándolo.
    """

    @pytest.mark.parametrize(
        "modulo",
        ["os", "sys", "subprocess", "socket", "requests", "httpx", "pickle", "ctypes",
         "importlib", "inspect", "threading"],
    )
    def test_should_marcar_como_critico_un_modulo_de_la_denegacion_explicita(
        self, modulo: str
    ) -> None:
        resultado = _auditar(f"import {modulo}\nresult = {{}}\n")

        assert resultado.risk_level == "CRITICAL", f"{modulo} quedó como revisable"
        assert resultado.puede_revisarse is False
        assert any(f.rule == "forbidden-module" for f in resultado.findings)

    @pytest.mark.parametrize("modulo", ["csv", "statistics", "decimal", "calendar"])
    def test_should_marcar_como_warning_un_modulo_solo_ausente_de_la_lista(
        self, modulo: str
    ) -> None:
        resultado = _auditar(f"import {modulo}\nresult = {{}}\n")

        assert resultado.risk_level == "WARNING", f"{modulo} quedó como bloqueante"
        assert resultado.puede_revisarse is True
        assert any(f.rule == "module-not-whitelisted" for f in resultado.findings)

    def test_should_aplicar_lo_mismo_a_un_from_import(self) -> None:
        assert _auditar("from os import getcwd\n").risk_level == "CRITICAL"
        assert _auditar("from csv import reader\n").risk_level == "WARNING"


# ---------------------------------------------------------------------------
# Rutas absolutas — lo que la aplicación nueva había perdido
# ---------------------------------------------------------------------------

class TestRutasAbsolutas:
    def test_should_bloquear_ruta_absoluta_de_windows_sin_llamada_prohibida(self) -> None:
        """Un script de informe solo puede leer el fichero que le pasa la plataforma.

        Aquí no hay `open()` ni ningún módulo prohibido: pandas está en la lista blanca y
        `read_excel` no es una llamada peligrosa. Lo único malo es la ruta.
        """
        codigo = (
            "import pandas as pd\n"
            "df = pd.read_excel('C:\\\\Users\\\\fabra\\\\datos.xlsx')\n"
            "result = {'tables': [], 'metrics': []}\n"
        )
        resultado = _auditar(codigo)

        assert resultado.risk_level == "CRITICAL"
        assert resultado.puede_revisarse is False
        assert any(f.rule == "absolute-path" for f in resultado.findings), resultado.findings

    def test_should_bloquear_ruta_absoluta_de_windows_con_barras(self) -> None:
        codigo = "import pandas as pd\ndf = pd.read_excel('C:/Users/fabra/datos.xlsx')\n"
        resultado = _auditar(codigo)

        assert resultado.risk_level == "CRITICAL"
        assert any(f.rule == "absolute-path" for f in resultado.findings)

    @pytest.mark.parametrize(
        "ruta",
        ["/etc/passwd", "/home/uji/datos.csv", "/var/log/syslog", "/proc/self/environ"],
    )
    def test_should_bloquear_rutas_absolutas_de_sistema_linux(self, ruta: str) -> None:
        codigo = f"import pandas as pd\ndf = pd.read_csv('{ruta}')\n"
        resultado = _auditar(codigo)

        assert resultado.risk_level == "CRITICAL", f"{ruta} pasó la auditoría"
        assert any(f.rule == "absolute-path" for f in resultado.findings)

    def test_should_no_confundir_una_url_con_una_ruta_de_windows(self) -> None:
        """`https://` lleva dentro `s:/`.

        La regex del legacy (`[a-zA-Z]:/`) marcaba como ruta absoluta de Windows cualquier
        URL escrita en un comentario, y el motivo que daba era falso. La letra de unidad
        tiene que ir precedida de algo que no sea alfanumérico.
        """
        codigo = (
            "import pandas as pd\n"
            "# Fuente de los datos: https://www.uji.es/normativa\n"
            "df = pd.read_excel(file_path)\n"
            "result = {'tables': [], 'metrics': []}\n"
        )
        resultado = _auditar(codigo)

        assert resultado.risk_level == "SAFE", resultado.findings

    def test_should_no_marcar_una_ruta_relativa(self) -> None:
        codigo = "import pandas as pd\ndf = pd.read_excel('datos/entrada.xlsx')\n"
        resultado = _auditar(codigo)

        assert resultado.risk_level == "SAFE", resultado.findings


# ---------------------------------------------------------------------------
# Número de línea — lo que convierte «hay un problema» en «está en la línea 14»
# ---------------------------------------------------------------------------

class TestNumeroDeLinea:
    def test_should_dar_la_linea_de_una_llamada_prohibida(self) -> None:
        codigo = (
            "import pandas as pd\n"
            "df = pd.read_excel(file_path)\n"
            "total = eval('1+1')\n"
            "result = {'tables': [], 'metrics': []}\n"
        )
        resultado = _auditar(codigo)

        hallazgo = next(f for f in resultado.findings if f.rule == "forbidden-call")
        assert hallazgo.line == 3
        assert hallazgo.detail == "eval"

    def test_should_dar_la_linea_de_un_modulo_no_permitido(self) -> None:
        codigo = "import pandas as pd\n\nimport csv\n"
        resultado = _auditar(codigo)

        hallazgo = next(f for f in resultado.findings if f.rule == "module-not-whitelisted")
        assert hallazgo.line == 3
        assert hallazgo.detail == "csv"
        assert hallazgo.severity == "WARNING"

    def test_should_dar_la_linea_de_una_ruta_absoluta(self) -> None:
        codigo = (
            "import pandas as pd\n"
            "# nada aquí\n"
            "# nada aquí tampoco\n"
            "df = pd.read_excel('C:\\\\datos.xlsx')\n"
        )
        resultado = _auditar(codigo)

        hallazgo = next(f for f in resultado.findings if f.rule == "absolute-path")
        assert hallazgo.line == 4

    def test_should_dar_la_linea_de_un_error_de_sintaxis(self) -> None:
        resultado = _auditar("import pandas as pd\ndf = pd.read_excel(\n")

        assert resultado.risk_level == "CRITICAL"
        assert resultado.puede_revisarse is False
        hallazgo = next(f for f in resultado.findings if f.rule == "syntax-error")
        assert hallazgo.line >= 1

    def test_should_llevar_mensaje_legible_en_cada_hallazgo(self) -> None:
        """El mensaje es lo que ve el administrador en la cola; lleva la línea dentro."""
        resultado = _auditar("import pandas as pd\ntotal = eval('1+1')\n")

        hallazgo = next(f for f in resultado.findings if f.rule == "forbidden-call")
        assert "eval" in hallazgo.message
        assert "2" in hallazgo.message


# ---------------------------------------------------------------------------
# El endurecimiento de SEC.8.3 sigue en pie
# ---------------------------------------------------------------------------

class TestEvasionesSiguenSiendoCriticas:
    @pytest.mark.parametrize(
        "codigo",
        [
            "__builtins__['eval']('1+1')",
            "().__class__.__bases__[0].__subclasses__()",
            "getattr(__builtins__, 'ev' + 'al')('1+1')",
            "globals()['__builtins__']",
        ],
    )
    def test_should_seguir_marcando_como_critica_cada_evasion(self, codigo: str) -> None:
        resultado = _auditar(codigo)

        assert resultado.risk_level == "CRITICAL", codigo
        assert resultado.puede_revisarse is False, (
            "una evasión del intérprete no la puede aceptar nadie mirándola"
        )
