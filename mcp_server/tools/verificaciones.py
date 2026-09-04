"""Tools MCP de las verificaciones de la plataforma (VAS.4).

Tres tools sobre los endpoints `Deploy: edge` del bloque VAS, para que un agente los use sin
escribir HTTP:

- `verificar_citas` → `POST /api/v1/verificaciones/citas` (VAS.1)
- `consultar_vigencia` → `GET /api/v1/verificaciones/vigencia` (VAS.2)
- `auditar_codigo` → `POST /api/v1/verificaciones/codigo` (VAS.3)
- `reglas_de_auditoria` → `GET /api/v1/verificaciones/codigo/reglas` (VAS.3)

Las cuatro con el token de cada cliente propagado por petición, igual que las de REG.4: el
servidor remoto no tiene credencial propia.

**Las firmas declaran los campos, no un `dict`.** Es la lección de REG.7: `evento: dict` daba un
esquema `{"type": "object", "additionalProperties": true}` —ni un nombre de campo, y encima
prometiendo que cualquier extra valía cuando el servidor los rechaza—, y un agente lo descubría a
base de 422 en bucle. Un guardarraíl del lado del servidor comprueba que estas firmas y los
contratos no divergen.

**Y `auditar_codigo` no pide confirmación**, igual que `registrar_actividad`: auditar no muta
nada, y una puerta delante de una tool que se llama antes de compartir cada script conseguiría
que se dejara de llamar.
"""
from __future__ import annotations

from typing import Annotated, Any, Callable

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from api_client import ApiClient

CITAS_PATH = "/api/v1/verificaciones/citas"
VIGENCIA_PATH = "/api/v1/verificaciones/vigencia"
CODIGO_PATH = "/api/v1/verificaciones/codigo"
REGLAS_PATH = "/api/v1/verificaciones/codigo/reglas"

ClientProvider = Callable[[], ApiClient]


async def run_verificar_citas_core(client: ApiClient, cuerpo: dict[str, Any]) -> dict:
    return await client.post(CITAS_PATH, json=cuerpo)


async def run_consultar_vigencia_core(
    client: ApiClient, parametros: dict[str, Any]
) -> dict:
    return await client.get(VIGENCIA_PATH, params=parametros)


async def run_auditar_codigo_core(client: ApiClient, cuerpo: dict[str, Any]) -> dict:
    return await client.post(CODIGO_PATH, json=cuerpo)


def register_verificaciones_tools(
    mcp: FastMCP, *, client_provider: ClientProvider
) -> None:
    @mcp.tool()
    async def verificar_citas(
        texto: Annotated[
            str,
            Field(
                description=(
                    "La respuesta a verificar, en markdown. Las citas se reconocen como enlaces "
                    "markdown: `[titulo](url)`."
                )
            ),
        ],
        fuentes_permitidas: Annotated[
            list[dict],
            Field(
                description=(
                    "Las fuentes que se entregaron a quien escribió el texto, como "
                    "`[{\"url\": \"...\", \"titulo\": \"...\"}]`. Sólo estas cuentan como "
                    "fundamento: una norma que el texto menciona pero que no se entregó no se "
                    "puede respaldar. Con la lista vacía no se verifica nada."
                )
            ),
        ],
        mensaje_sin_respuesta: Annotated[
            str | None,
            Field(
                description=(
                    "Qué devolver si no queda ninguna cita válida. Si no se indica, el mensaje "
                    "de rendición de la plataforma. Ponlo en la lengua de la pregunta."
                )
            ),
        ] = None,
    ) -> dict:
        """Aplica el contrato de citas de la plataforma a un texto. [scope verificaciones:use]

        La regla es «ninguna afirmación sin fuente resoluble», y hace tres cosas en este orden:
        una cita al documento correcto con un ancla que no se entregó **baja al documento y
        sobrevive**; lo que apunta fuera del conjunto entregado **pierde el enlace pero conserva
        la mención**; y sólo entonces se comprueba si queda alguna cita válida.

        Devuelve `cumple`, el `texto_resultante` —que si no cumple es el mensaje de rendición— y
        el desglose: `citas_validas`, `citas_invalidas`, `remisiones_despojadas` y
        `anclas_degradadas`. Es el mismo veredicto que el asistente aplica a sus respuestas.
        """
        cuerpo: dict[str, Any] = {
            "texto": texto,
            "fuentes_permitidas": fuentes_permitidas,
        }
        if mensaje_sin_respuesta is not None:
            cuerpo["mensaje_sin_respuesta"] = mensaje_sin_respuesta
        return await run_verificar_citas_core(client_provider(), cuerpo)

    @mcp.tool()
    async def consultar_vigencia(
        document_id: Annotated[
            str | None,
            Field(description="El identificador del documento en el corpus."),
        ] = None,
        url: Annotated[
            str | None,
            Field(
                description=(
                    "La URL canónica del documento. La barra final, el esquema y el ancla no "
                    "importan. Indica esto **o** `document_id`, no los dos."
                )
            ),
        ] = None,
    ) -> dict:
        """Si la plataforma pondría un aviso de vigencia sobre un documento, y cuál.
        [scope verificaciones:use]

        Devuelve el estado, quién validó la vigencia y cuándo, y **el texto del aviso** —no un
        booleano—: si cada aplicación redactara el suyo, dos superficies de la misma institución
        acabarían diciendo cosas distintas de la misma norma.

        Un documento que no sea de tu organización, o que el corpus no ofrezca a los asistentes,
        responde 404 y no «no validado»: decir «existe pero no puedo contarte» ya sería contar
        que existe.
        """
        parametros = {
            nombre: valor
            for nombre, valor in (("document_id", document_id), ("url", url))
            if valor is not None
        }
        return await run_consultar_vigencia_core(client_provider(), parametros)

    @mcp.tool()
    async def auditar_codigo(
        codigo: Annotated[
            str,
            Field(
                description=(
                    "El script de Python a auditar. **No se guarda**: la plataforma se queda "
                    "sólo con su SHA-256, que es lo que permite cotejar después sin tener el "
                    "código."
                )
            ),
        ],
        finalidad: Annotated[
            str | None,
            Field(
                description=(
                    "Para qué se audita, en una frase. Va al registro de actividad junto al "
                    "nivel de riesgo y el hash; no cambia el veredicto, que es determinista."
                )
            ),
        ] = None,
    ) -> dict:
        """Audita un script con la vara del catálogo de funciones. [scope verificaciones:use]

        Es la revisión posterior del nivel 2 de la Instrucció 02/2026 para código que **no** va a
        correr en la plataforma: análisis del AST contra la lista blanca de módulos y las
        capacidades que ninguna revisión humana acepta.

        Devuelve el nivel —`SAFE`, `WARNING` o `CRITICAL`—, cada hallazgo con su regla y su
        línea, si `puede_revisarse` por una persona, y el `code_sha256`. Un `WARNING` es un hueco
        en una lista y lo puede aceptar quien revise; un `CRITICAL` no.

        **Deja constancia en el registro de actividad de la organización**, con el hash y el
        nivel: auditar es un acto de gobernanza. Pide primero `reglas_de_auditoria` si quieres
        saber con qué se puede escribir código que pase.
        """
        cuerpo: dict[str, Any] = {"codigo": codigo}
        if finalidad is not None:
            cuerpo["finalidad"] = finalidad
        return await run_auditar_codigo_core(client_provider(), cuerpo)

    @mcp.tool()
    async def reglas_de_auditoria() -> dict:
        """Con qué se puede escribir código que pase la auditoría. [scope verificaciones:use]

        Los módulos permitidos, las capacidades denegadas, las reglas con su nivel y una
        `version_auditor` que cambia si la caja de herramientas cambia — guárdala para saber si
        tienes que volver a leerla.

        Se compone leyendo las listas del propio auditor, así que no puede quedarse atrás
        respecto de lo que la auditoría hace de verdad.
        """
        return await client_provider().get(REGLAS_PATH)
