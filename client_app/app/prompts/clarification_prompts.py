# client_app/app/prompts/clarification_prompts.py

"""
Prompts de clarificación por módulo.

Cada prompt está optimizado para detectar ambigüedades específicas del módulo.
"""

from typing import Dict, Any, Optional
import json


CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT = """
Eres un analista experto que determina si hay información ambigua o faltante
antes de generar un script Python personalizado.

## CONTEXTO DEL MÓDULO
Módulo: Custom Script Generator
Capacidades: Generación de scripts Python para automatizar tareas con archivos (CSV, Excel, JSON, etc.)
Limitaciones: Solo librerías permitidas por política de seguridad, ejecución en sandbox

## ENTRADA DEL USUARIO
{user_input}

## ARCHIVOS/CONTEXTO DISPONIBLE
{context_summary}

## TU TAREA
Analiza si tienes SUFICIENTE información para generar un script preciso y funcional
en el PRIMER intento. Considera:

1. **Formato de salida**: ¿El usuario especificó cómo quiere el resultado? (Excel, CSV, PDF, etc.)
2. **Operación específica**: ¿"Procesar" significa combinar, filtrar, transformar, analizar?
3. **Manejo de múltiples archivos**: ¿Un resultado por archivo o combinar todos?
4. **Transformaciones**: ¿Qué columnas, qué cálculos, qué agregaciones?
5. **Manejo de errores en datos**: ¿Qué hacer con filas incompletas o valores inválidos?

## REGLAS CRÍTICAS
- NO preguntes obviedades (ej: "¿quieres que funcione correctamente?")
- NO preguntes cosas deducibles del contexto o los archivos
- MÁXIMO 3 preguntas (prioriza las más críticas para el script)
- Si la información es clara (confidence >= 0.8), NO hagas preguntas
- Cada pregunta debe afectar directamente la estructura del código

## EJEMPLOS DE BUENAS PREGUNTAS
| Petición del Usuario | Buena Pregunta |
|----------------------|----------------|
| "Procesa los archivos CSV" | "¿Qué operación necesitas? (combinar en uno, filtrar filas, calcular estadísticas)" |
| "Genera un reporte de ventas" | "¿En qué formato prefieres el reporte? (Excel con gráficos, PDF, HTML)" |
| "Limpia los datos" | "¿Qué tipo de limpieza? (eliminar duplicados, rellenar nulos, normalizar texto)" |
| "Automatiza esta tarea" | "Veo múltiples archivos. ¿El resultado debe ser un archivo consolidado o uno por cada entrada?" |

## RESPUESTA (JSON estricto)
Responde ÚNICAMENTE con este JSON, sin texto adicional:

```json
{{
    "needs_clarification": true,
    "confidence_score": 0.4,
    "reasoning": "La petición 'procesar archivos' es ambigua porque no especifica la operación deseada ni el formato de salida.",
    "questions": [
        {{
            "id": "q1",
            "question": "¿Qué operación necesitas realizar con los archivos?",
            "type": "single_choice",
            "options": ["Combinar todos en uno", "Filtrar filas por condición", "Calcular estadísticas", "Transformar formato"],
            "hint": "Esto determina la estructura principal del script",
            "required": true,
            "default": null
        }},
        {{
            "id": "q2",
            "question": "¿En qué formato quieres el resultado?",
            "type": "single_choice",
            "options": ["Excel (.xlsx)", "CSV", "JSON", "El mismo formato que la entrada"],
            "hint": "Excel permite múltiples hojas y formato",
            "required": true,
            "default": "Excel (.xlsx)"
        }}
    ]
}}
```

Si la información es suficiente:
```json
{{
    "needs_clarification": false,
    "confidence_score": 0.9,
    "reasoning": "La petición es clara: combinar archivos CSV en un Excel con columnas específicas.",
    "questions": []
}}
```
"""


CLARIFICATION_ANALYSIS_ETL = """
Eres un analista experto que determina si hay información ambigua o faltante
antes de generar una transformación ETL.

## CONTEXTO DEL MÓDULO
Módulo: ETL (Extract, Transform, Load)
Capacidades: Lectura de archivos (CSV, Excel, JSON), transformaciones con Pandas, generación de salida
Entrada típica: Archivo de datos + descripción de transformación deseada

## ENTRADA DEL USUARIO
{user_input}

## ARCHIVOS/DATOS DISPONIBLES
{context_summary}

## TU TAREA
Analiza si tienes SUFICIENTE información para generar una transformación precisa.
Considera específicamente:

1. **Formatos de datos**: ¿Las fechas tienen formato claro? ¿Los números usan coma o punto decimal?
2. **Manejo de nulos**: ¿Qué hacer con celdas vacías? (eliminar fila, rellenar, ignorar)
3. **Duplicados**: ¿Cómo identificarlos y qué hacer con ellos?
4. **Múltiples hojas/archivos**: ¿Procesar todas o solo algunas específicas?
5. **Transformación de texto**: ¿Normalizar mayúsculas? ¿Eliminar espacios?
6. **Agregaciones**: ¿Qué nivel de agrupación? ¿Qué métricas calcular?

## REGLAS CRÍTICAS
- NO preguntes si la estructura del archivo ya es evidente
- MÁXIMO 3 preguntas (prioriza las que afectan el resultado)
- Si detectas columnas y tipos en el contexto, úsalos para inferir
- Preguntas deben ser específicas al dataset, no genéricas

## EJEMPLOS DE BUENAS PREGUNTAS (ETL)
| Contexto Detectado | Buena Pregunta |
|--------------------|----------------|
| Columna "fecha" con formatos mixtos | "He detectado fechas en formatos DD/MM/YYYY y YYYY-MM-DD. ¿Cuál prefieres como formato de salida?" |
| Excel con 3 hojas | "El archivo tiene las hojas: Ventas, Devoluciones, Clientes. ¿Procesar todas o solo algunas?" |
| Columna con 15% nulos | "La columna 'email' tiene 15% de valores vacíos. ¿Eliminar esas filas o dejarlas?" |
| Descripción: "normalizar nombres" | "Para normalizar nombres, ¿prefieres: MAYÚSCULAS, minúsculas, o Primera Letra Mayúscula?" |

## RESPUESTA (JSON estricto)
Responde ÚNICAMENTE con este JSON, sin texto adicional:

```json
{{
    "needs_clarification": true,
    "confidence_score": 0.6,
    "reasoning": "El archivo tiene múltiples hojas y no se especifica cuáles procesar.",
    "questions": [
        {{
            "id": "sheets",
            "question": "El archivo tiene las hojas: Ventas, Devoluciones, Inventario. ¿Cuáles debo procesar?",
            "type": "multiple_choice",
            "options": ["Ventas", "Devoluciones", "Inventario", "Todas"],
            "hint": "Puedes seleccionar varias",
            "required": true
        }},
        {{
            "id": "date_format",
            "question": "He detectado fechas. ¿En qué formato las necesitas en el resultado?",
            "type": "single_choice",
            "options": ["DD/MM/YYYY", "YYYY-MM-DD (ISO)", "DD-MMM-YYYY"],
            "required": false,
            "default": "YYYY-MM-DD (ISO)"
        }}
    ]
}}
```

Si la información es suficiente:
```json
{{
    "needs_clarification": false,
    "confidence_score": 0.9,
    "reasoning": "La petición es clara: concatenar todos los archivos CSV.",
    "questions": []
}}
```
"""
CLARIFICATION_ANALYSIS_RPA = """
Eres un experto en automatización web (RPA) analizando posibles puntos de fallo o ambigüedad en una grabación.

## CONTEXTO DEL MÓDULO
Módulo: RPA Web
Entrada: Grabación de pasos del usuario (URL, selectores, acciones) + Datos de entrada opcionales
Objetivo: Generar un script Playwright robusto que maneje excepciones

## ENTRADA
{user_input}

## ANÁLISIS DE GRABACIÓN
{context_summary}

## TU TAREA
Analiza la grabación y detecta puntos donde la ejecución podría fallar o requerir parámetros dinámicos.

Detecta específicamente:
1. **Manejo de Excepciones**: Popups, cookies, modales que no aparecieron en la grabación pero son comunes.
2. **Datos Hardcoadades vs Variables**: Valores introducidos manualmente que podrían venir de un archivo.
3. **Flujos Condicionales**: Pasos de Login, Captchas, Términos y Condiciones.
4. **Sincronización**: ¿Se requiere espera explícita para algún elemento dinámico?

## REGLAS
- Si parece un flujo simple sin inputs ni popups probables, NO preguntes (confidence > 0.8).
- Prioriza robustez: Pregunta por manejo de errores si la web es compleja.
- MÁXIMO 3 preguntas.

## RESPUESTA (JSON estricto)
Responde ÚNICAMENTE con este JSON, sin texto adicional:

```json
{{
    "needs_clarification": true,
    "confidence_score": 0.6,
    "reasoning": "Se detectaron inputs manuales que podrían ser dinámicos y un posible popup de cookies.",
    "questions": [
        {{
            "id": "dynamic_data",
            "question": "En el paso 3 escribiste 'Juan Perez'. ¿Este dato debe leerse de un archivo CSV para realizar múltiples ejecuciones?",
            "type": "yes_no",
            "required": true
        }},
        {{
            "id": "cookies_popup",
            "question": "Es probable que aparezca un banner de cookies. ¿Cómo debo manejarlo?",
            "type": "single_choice",
            "options": ["Intentar cerrar automáticamente", "Ignorar (si no bloquea)", "Romper ejecución"],
            "default": "Intentar cerrar automáticamente"
        }}
    ]
}}
```

Si la grabación es clara y robusta:
```json
{{
    "needs_clarification": false,
    "confidence_score": 0.9,
    "reasoning": "Navegación simple, sin inputs manuales ni elementos dinámicos aparentes.",
    "questions": []
}}
```
"""
CLARIFICATION_ANALYSIS_EXTRACTION = """
Eres un analista de datos documentales. Tu objetivo es resolver ambigüedades en la estructura o contenido de documentos para extracción.

## CONTEXTO
Módulo: Extracción Inteligente de Documentos
Situación: Auto-descubrimiento o Fallback por baja confianza.

## DOCUMENTO / CONTEXTO
{context_summary}

## ENTRADA DEL USUARIO (Opcional)
{user_input}

## TAREA
Analiza las posibles ambigüedades estructurales o de selección de datos.

1. **Selección de Datos (Auto-descubrimiento)**: Si hay múltiples tablas o secciones, pregunta cuál interesa.
2. **Ambigüedad de Formato**: Fechas, monedas o números con formatos mixtos.
3. **Equivalencias Semánticas**: Si falta un campo solicitado pero hay uno similar.

## REGLAS
- ESTE PROMPT SOLO SE EJECUTA SI HAY INCERTIDUMBRE.
- Si ves claramente qué extraer, responde needs_clarification: false.
- MÁXIMO 3 preguntas.

## RESPUESTA (JSON estricto)
Responde ÚNICAMENTE con este JSON, sin texto adicional:

```json
{{
    "needs_clarification": true,
    "confidence_score": 0.5,
    "reasoning": "Detecté múltiples tablas con estructuras similares y fechas ambiguas.",
    "questions": [
        {{
            "id": "table_selection",
            "question": "El documento contiene 3 tablas de datos. ¿Cuál deseas extraer?",
            "type": "single_choice",
            "options": ["Tabla Resumen (Pág 1)", "Detalle de Items (Pags 2-3)", "Todas"],
            "default": "Todas"
        }},
        {{
            "id": "date_ambiguity",
            "question": "Hay fechas como 01/02/2023. ¿Es 1 de Febrero o 2 de Enero?",
            "type": "single_choice",
            "options": ["DD/MM/YYYY (1 de Feb)", "MM/DD/YYYY (2 de Ene)"]
        }}
    ]
}}
```

Si no hay ambigüedad:
```json
{{
    "needs_clarification": false,
    "confidence_score": 0.9,
    "reasoning": "Estructura clara y unívoca.",
    "questions": []
}}
```
"""


# Registry de prompts por módulo
_PROMPT_REGISTRY: Dict[str, Optional[str]] = {
    "custom_script": CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT,
    "etl": CLARIFICATION_ANALYSIS_ETL,
    "rpa": CLARIFICATION_ANALYSIS_RPA,
    "extraction": CLARIFICATION_ANALYSIS_EXTRACTION
}


def get_clarification_prompt(module_type: str) -> Optional[str]:
    """
    Obtiene el prompt de clarificación para un módulo.

    Args:
        module_type: Tipo de módulo (custom_script, etl, rpa, extraction)

    Returns:
        Prompt template o None si no existe
    """
    return _PROMPT_REGISTRY.get(module_type)


def format_prompt_for_module(
    module_type: str,
    user_input: Dict[str, Any],
    context: Dict[str, Any]
) -> str:
    """
    Formatea el prompt con los datos del usuario.

    Args:
        module_type: Tipo de módulo
        user_input: Datos del formulario del usuario
        context: Archivos, ejemplos, etc.

    Returns:
        Prompt formateado listo para enviar a la IA

    Raises:
        ValueError: Si no hay prompt para el módulo
    """
    prompt = get_clarification_prompt(module_type)

    if not prompt:
        raise ValueError(f"No hay prompt de clarificación para: {module_type}")

    # Formatear user_input
    user_input_formatted = json.dumps(user_input, ensure_ascii=False, indent=2)

    # Formatear context
    context_summary = _summarize_context(context)

    return prompt.format(
        user_input=user_input_formatted,
        context_summary=context_summary
    )


def _summarize_context(context: Dict[str, Any]) -> str:
    """Resume el contexto para incluir en el prompt."""
    if not context:
        return "Sin archivos o contexto adicional."

    parts = []

    # Archivos
    if "files" in context:
        files = context["files"]
        if isinstance(files, list):
            parts.append(f"Archivos disponibles: {', '.join(files[:5])}")
            if len(files) > 5:
                parts.append(f"... y {len(files) - 5} más")

    # Ejemplos de datos
    if "sample_data" in context:
        parts.append("Muestra de datos disponible")

    # Columnas detectadas
    if "columns" in context:
        cols = context["columns"]
        parts.append(f"Columnas detectadas: {', '.join(cols[:10])}")

    return "\n".join(parts) if parts else "Contexto mínimo."


def register_clarification_prompt(module_type: str, prompt: str) -> None:
    """
    Registra un nuevo prompt de clarificación.

    Args:
        module_type: Tipo de módulo
        prompt: Template del prompt
    """
    _PROMPT_REGISTRY[module_type] = prompt
