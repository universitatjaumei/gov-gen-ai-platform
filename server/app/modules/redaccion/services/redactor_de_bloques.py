"""Adaptador entre el modelo y el nodo de redacción del grafo (VER.1). Deploy: edge.

`AIAssistDraftNode` invoca `llm.generate(prompt=<ai_prompt_template_id>, context=...)`, y ese
`prompt` **no es un prompt**: es el identificador de una plantilla. En el módulo de redacción
no había nada que lo resolviera —`hub_prompt_templates` cuelga de un chatbot y es otra
cosa—, así que cablear el modelo sin resolverlo sería pedirle que redacte un informe con la
instrucción «generic_report_v1».

El catálogo vive aquí, como dato del módulo, y es deliberadamente pequeño: hoy los perfiles
solo declaran un identificador. Cuando haya que editarlos desde el panel, esto es lo que se
sustituye por una tabla, sin tocar el grafo.
"""
from __future__ import annotations

from typing import Any

from server.app.core.llm_text import texto_de

_SISTEMA = (
    "Eres un redactor de informes institucionales de una universidad pública. Redactas en "
    "la lengua del contexto que se te da. Te apoyas ÚNICAMENTE en los datos del contexto: "
    "no añades cifras, fechas ni nombres que no aparezcan en él, y si un dato falta lo dices "
    "en vez de inventarlo. El tono es sobrio y administrativo, sin adjetivos valorativos."
)

CATALOGO_DE_PROMPTS: dict[str, str] = {
    "generic_report_v1": (
        "Redacta esta sección del informe a partir de los datos extraídos que figuran en el "
        "contexto. Empieza por lo que responde a la finalidad de la sección, apoya cada "
        "afirmación en un dato del contexto y cierra sin conclusiones que los datos no "
        "sostengan. No repitas las tablas: interprétalas."
    ),
}

_SIN_CATALOGO = (
    "Redacta esta sección del informe a partir de los datos del contexto, apoyando cada "
    "afirmación en uno de ellos. La plantilla de prompt «{prompt_id}» no está en el catálogo "
    "del módulo, así que se usa la instrucción genérica."
)


def instruccion_para(prompt_id: str) -> str:
    """La instrucción real que corresponde a un `ai_prompt_template_id`.

    Cuando el identificador no está en el catálogo **viaja dentro de la instrucción** en vez
    de desaparecer: es lo único que permite saber después qué plantilla pidió esa redacción,
    y deja el hueco a la vista en lugar de degradarse en silencio.
    """
    if prompt_id in CATALOGO_DE_PROMPTS:
        return CATALOGO_DE_PROMPTS[prompt_id]
    return _SIN_CATALOGO.format(prompt_id=prompt_id)


class RedactorDeBloques:
    """Implementa el protocolo `LLMService` que espera `AIAssistDraftNode`.

    `model_name` no es decorativo: el nodo lo guarda en el bloque como `model_used`, y es lo
    que permite saber con qué modelo se redactó un informe meses después.
    """

    def __init__(self, modelo: Any, model_name: str) -> None:
        self._modelo = modelo
        self.model_name = model_name

    async def generate(self, prompt: str, context: str) -> str:
        respuesta = await self._modelo.ainvoke([
            {"role": "system", "content": _SISTEMA},
            {
                "role": "user",
                "content": (
                    f"{instruccion_para(prompt)}\n\n"
                    f"--- DATOS EXTRAÍDOS ---\n{context}"
                ),
            },
        ])
        return texto_de(getattr(respuesta, "content", respuesta))
