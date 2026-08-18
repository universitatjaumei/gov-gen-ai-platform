"""SEG.2 — la instrucción de valorar una tendencia, con sus reglas duras.

El catálogo del módulo tenía una sola instrucción, `generic_report_v1`: «redacta esta sección».
Lo que estos informes necesitan es otra cosa y muy concreta: **comparar el último curso con los
anteriores sobre una tabla**, decir si la tendencia crece o decrece y, cuando decrece, sugerir
acciones sin imperativos.

Las reglas se **portan del prompt de la gema** que se usó antes, igual que se portaron la
auditoría graduada y las operaciones de limpieza del legacy de AutomatIA. Ese prompt las
escribía en mayúsculas —«NO HAGAS CÁLCULOS COMO MEDIAS SI NO SE TE PIDE»— porque era lo único
que tenía; aquí, además, hay tests.
"""
from __future__ import annotations

import pytest

from server.app.modules.redaccion.services.redactor_de_bloques import (
    CATALOGO_DE_PROMPTS,
    PROMPT_RESUMEN_DE_RESULTADOS,
    PROMPT_VALORACION_DE_TENDENCIA,
    instruccion_para,
)

#: Tabla 1.3 del informe real de un programa de doctorado, literal.
_TABLA_REAL = """\
| Indicador | 2024 | 2023 | 2022 |
| :---- | :---- | :---- | :---- |
| TASA DE OFERTA Y DEMANDA DOCTORADO | 46.67 | 102.22 | 48.33 |
| TASA ABANDONO DOCTORADO A TIEMPO COMPLETO | 21.21 | 15.15 | 4.76 |
| TASA DE MATRICULACIÓN DOCTORADO | 45.00 | 68.33 | 57.78 |

Tabla 1.3 Evolución de los indicadores del programa
"""

#: Tabla 1.4.2 del mismo informe: dos filas enteras sin dato en el último curso.
_TABLA_CON_HUECOS = """\
| Indicador | 2024 | 2023 | 2022 | 2021 |
| :---- | :---- | :---- | :---- | :---- |
| El contenido de las actividades formativas específicas | No hay valor | 4.20 | No hay valor | 4.30 |

Tabla 1.4.2 Satisfacción con las actividades formativas
"""


# ----------------------------------------------------------------------
# Las dos instrucciones existen y se resuelven
# ----------------------------------------------------------------------


def test_las_dos_instrucciones_estan_en_el_catalogo() -> None:
    assert PROMPT_VALORACION_DE_TENDENCIA in CATALOGO_DE_PROMPTS
    assert PROMPT_RESUMEN_DE_RESULTADOS in CATALOGO_DE_PROMPTS


def test_pedir_la_valoracion_de_tendencia_no_cae_en_la_generica() -> None:
    """Si el identificador no se resolviera, el modelo recibiría «redacta esta sección»."""
    instruccion = instruccion_para(PROMPT_VALORACION_DE_TENDENCIA)
    assert "no está en el catálogo" not in instruccion


@pytest.mark.parametrize(
    "fragmento",
    [
        "no calcules",          # ni medias ni totales que no vengan dados
        "No hay valor",         # la ausencia se respeta y se dice
        "no uses imperativos",  # las sugerencias son sugerencias
        "hipótesis",            # una relación entre variables se marca como tal
    ],
)
def test_la_instruccion_lleva_sus_reglas_duras(fragmento: str) -> None:
    """Cada regla viene de un fallo real del intento anterior, no de una preferencia de estilo."""
    instruccion = instruccion_para(PROMPT_VALORACION_DE_TENDENCIA).lower()
    assert fragmento.lower() in instruccion, f"falta la regla: {fragmento}"


def test_la_instruccion_deja_la_reflexion_cualitativa_a_quien_firma() -> None:
    instruccion = instruccion_para(PROMPT_VALORACION_DE_TENDENCIA).lower()
    assert "quien firma" in instruccion or "responsable" in instruccion


@pytest.mark.parametrize(
    "identificador",
    [PROMPT_VALORACION_DE_TENDENCIA, PROMPT_RESUMEN_DE_RESULTADOS],
)
def test_las_dos_instrucciones_piden_prosa_y_no_markdown(identificador: str) -> None:
    """SEG.5 — visto en el informe real: el modelo devolvía `**Producción vegetal:**` y viñetas
    con asteriscos, y el informe los imprimía tal cual, con los asteriscos a la vista.
    """
    instruccion = instruccion_para(identificador).lower()
    assert "markdown" in instruccion
    assert "asterisco" in instruccion


@pytest.mark.parametrize(
    "identificador",
    [PROMPT_VALORACION_DE_TENDENCIA, PROMPT_RESUMEN_DE_RESULTADOS],
)
def test_las_dos_instrucciones_acotan_la_extension(identificador: str) -> None:
    """La valoración de una tabla son unas frases. Sin acotarlo salía un ensayo por tabla, con
    apartados propios («Conclusión», «Sugerencias de mejora»), que nadie revisa nueve veces.
    """
    instruccion = instruccion_para(identificador).lower()
    assert "párrafo" in instruccion


def test_el_resumen_de_resultados_admite_varias_tablas() -> None:
    """Los apartados que agregan tablas necesitan otra instrucción, no la de una sola."""
    instruccion = instruccion_para(PROMPT_RESUMEN_DE_RESULTADOS).lower()
    assert "varias tablas" in instruccion or "las tablas" in instruccion


# ----------------------------------------------------------------------
# Contra las tablas reales, con un modelo de verdad simulado
# ----------------------------------------------------------------------


class _ModeloQueObedece:
    """Devuelve lo que un modelo dócil devolvería con esa instrucción, para fijar el contrato.

    No prueba al modelo —eso es la verificación con modelo real de SEG.5—: prueba que la
    instrucción y el contexto llegan completos y que el redactor no los recorta.
    """

    def __init__(self) -> None:
        self.mensaje_de_usuario: str | None = None
        self.sistema: str | None = None

    async def ainvoke(self, mensajes: list[dict]) -> object:
        self.sistema = next(m["content"] for m in mensajes if m["role"] == "system")
        self.mensaje_de_usuario = next(m["content"] for m in mensajes if m["role"] == "user")
        return type("R", (), {"content": "Valoración."})()

    #: El redactor compone «instrucción + separador + datos». Se parte por el separador porque
    #: la propia instrucción menciona «No hay valor», y contar sobre el mensaje entero mezclaría
    #: lo que se le pide al modelo con lo que se le da.
    _SEPARADOR = "--- DATOS EXTRAÍDOS ---"

    @property
    def instruccion(self) -> str | None:
        """Lo que el redactor puso delante de los datos: la instrucción ya resuelta."""
        if self.mensaje_de_usuario is None:
            return None
        return self.mensaje_de_usuario.split(self._SEPARADOR)[0]

    @property
    def contexto(self) -> str | None:
        """Sólo los datos, sin la instrucción."""
        if self.mensaje_de_usuario is None:
            return None
        partes = self.mensaje_de_usuario.split(self._SEPARADOR)
        return partes[1] if len(partes) > 1 else partes[0]


@pytest.mark.asyncio
async def test_el_redactor_entrega_la_instruccion_resuelta_y_la_tabla_entera() -> None:
    """La instrucción que viaja al modelo es la del catálogo, no el identificador."""
    from server.app.modules.redaccion.services.redactor_de_bloques import RedactorDeBloques

    modelo = _ModeloQueObedece()
    redactor = RedactorDeBloques(modelo, "modelo-de-prueba")

    await redactor.generate(prompt=PROMPT_VALORACION_DE_TENDENCIA, context=_TABLA_REAL)

    assert modelo.instruccion is not None
    assert "no calcules" in modelo.instruccion.lower(), "la instrucción no se ha resuelto"
    # La tabla llega completa: las tres tasas y los tres cursos.
    assert "102.22" in modelo.contexto
    assert "TASA ABANDONO DOCTORADO A TIEMPO COMPLETO" in modelo.contexto


@pytest.mark.asyncio
async def test_una_tabla_con_huecos_llega_con_sus_huecos() -> None:
    """«No hay valor» tiene que sobrevivir hasta el modelo: es la diferencia entre no hay dato
    y el dato es cero, y el intento anterior la perdía."""
    from server.app.modules.redaccion.services.redactor_de_bloques import RedactorDeBloques

    modelo = _ModeloQueObedece()
    await RedactorDeBloques(modelo, "m").generate(
        prompt=PROMPT_VALORACION_DE_TENDENCIA, context=_TABLA_CON_HUECOS
    )

    assert modelo.contexto.count("No hay valor") == 2
