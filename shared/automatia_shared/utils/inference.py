"""
Motor de inferencia de contratos atomicos.
Prompt #1: Analiza codigo fuente en busca de marcadores {{variable}} y genera UIContract.
Prompt #5: Analiza objetos JSON y genera UIContract con tipos inferidos.
"""
import re
import json
from typing import Optional, List, Union, Dict, Any
from automatia_shared.contracts.ui_contract import UIContract, InputDefinition, InputType
from automatia_shared.utils import flatten_dict


# Regex para detectar patrones {{variable}} con espacios opcionales
PLACEHOLDER_PATTERN = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')


def _humanize_label(name: str) -> str:
    """
    Convierte un nombre snake_case a una etiqueta legible.
    Ejemplo: nombre_cliente -> Nombre Cliente
    """
    return ' '.join(word.capitalize() for word in name.split('_'))


def infer_contract_from_source(source_code: Optional[str]) -> UIContract:
    """
    Analiza el código fuente de un script para detectar variables y generar un contrato UI.

    Busca marcadores de posición con el formato `{{nombre_variable}}` y genera un
    `UIContract` de Pydantic. Todas las variables detectadas se mapean a tipos
    `STR` por defecto.

    Args:
        source_code (Optional[str]): Código fuente (Python o Markdown) a analizar.
            Puede ser None o una cadena vacía.

    Returns:
        UIContract: Contrato con los inputs detectados. Si no hay variables o el
            código es nulo/vacío, retorna un contrato sin inputs.

    Especificaciones:
        - Regex de detección: `{{ \\s* ([a-zA-Z_][a-zA-Z0-9_]*) \\s* }}`.
        - Deduplicación: Las variables repetidas aparecen una sola vez en el contrato.
        - Orden: Se mantiene el orden de aparición en el texto original.
        - Robustez: Maneja `None` y cadenas vacías sin lanzar excepciones.
    """
    # Manejo de valores nulos o vacios
    if not source_code:
        return UIContract(inputs=[])

    # Encontrar todas las coincidencias
    matches = PLACEHOLDER_PATTERN.findall(source_code)

    # Deduplicar manteniendo el orden de aparicion
    seen = set()
    unique_vars: List[str] = []
    for var_name in matches:
        if var_name not in seen:
            # Validar que es un identificador Python valido
            if var_name.isidentifier():
                seen.add(var_name)
                unique_vars.append(var_name)

    # Construir lista de InputDefinition
    inputs = [
        InputDefinition(
            name=var_name,
            label=_humanize_label(var_name),
            type=InputType.STR,
            required=True,
            description=f"Variable detectada automaticamente: {var_name}"
        )
        for var_name in unique_vars
    ]

    return UIContract(inputs=inputs)


# =============================================================================
# Prompt #5: Inferencia desde JSON
# =============================================================================

# Regex para detectar formatos de fecha
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?$')


def _humanize_label_with_dots(name: str) -> str:
    """
    Convierte un nombre con snake_case y dot notation a etiqueta legible.
    Ejemplo: pedido.cliente.nombre -> Pedido Cliente Nombre
    """
    # Reemplazar puntos por espacios y luego humanizar cada parte
    parts = name.replace('.', ' ').split('_')
    return ' '.join(word.capitalize() for word in ' '.join(parts).split())


def _infer_type_from_value(value: Any) -> InputType:
    """
    Infiere el InputType apropiado basandose en el valor Python.

    Mapeo:
        - bool -> BOOL (debe ir antes de int porque bool es subclase de int)
        - int -> INT
        - float -> FLOAT
        - str con formato YYYY-MM-DD -> DATE
        - str con formato YYYY-MM-DDTHH:MM:SS -> DATETIME
        - str -> STR
        - None -> STR (por defecto)
        - list/dict -> STR (se tratara como JSON string)
    """
    if value is None:
        return InputType.STR

    if isinstance(value, bool):
        return InputType.BOOL

    if isinstance(value, int):
        return InputType.INT

    if isinstance(value, float):
        return InputType.FLOAT

    if isinstance(value, str):
        # Detectar fechas
        if DATETIME_PATTERN.match(value):
            return InputType.DATETIME
        if DATE_PATTERN.match(value):
            return InputType.DATE
        return InputType.STR

    # Para listas y diccionarios, tratarlos como STR (JSON)
    return InputType.STR


def infer_contract_from_json(data: Union[Dict[str, Any], List[Any], str, None]) -> UIContract:
    """
    Analiza un objeto JSON y genera un UIContract que representa su estructura.

    Este método infiere tipos automáticamente (INT, FLOAT, DATE, DATETIME, BOOL, STR)
    y gestiona diccionarios anidados mediante el aplanamiento de claves con
    notación de puntos o guiones bajos.

    Args:
        data (Union[Dict, List, str, None]): Datos de entrada. Puede ser un dicccionario,
            una lista (se toma el primer elemento), una cadena JSON o None.

    Returns:
        UIContract: Contrato con los inputs detectados y tipados según los valores.

    Especificaciones:
        - Detección de fechas: Identifica formatos YYYY-MM-DD (DATE) e ISO (DATETIME).
        - Aplanamiento: Genera claves aplanadas para representar estructuras anidadas.
        - Labels: Convierte `snake_case` y notación de puntos a etiquetas legibles.
    """
    # Manejo de None
    if data is None:
        return UIContract(inputs=[])

    # Si es string, intentar parsear como JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return UIContract(inputs=[])

    # Si es lista, tomar el primer elemento
    if isinstance(data, list):
        if not data:
            return UIContract(inputs=[])
        data = data[0]

    # Si no es dict en este punto, retornar vacio
    if not isinstance(data, dict):
        return UIContract(inputs=[])

    # Si el dict esta vacio
    if not data:
        return UIContract(inputs=[])

    # Aplanar el diccionario para manejar anidacion
    # Usamos '_' como separador para que el nombre sea un identificador Python valido
    flat_data = flatten_dict(data, sep='_')

    # Construir lista de InputDefinition
    inputs = []
    for key, value in flat_data.items():
        input_type = _infer_type_from_value(value)
        inputs.append(
            InputDefinition(
                name=key,
                label=_humanize_label_with_dots(key),
                type=input_type,
                required=True,
                description=f"Campo inferido desde JSON: {key}"
            )
        )

    return UIContract(inputs=inputs)
