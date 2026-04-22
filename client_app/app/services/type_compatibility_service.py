"""
Type Compatibility Service - Prompt #10 Implementation
Logica de "Sugerencia de Puentes" para Contratos Incompatibles.

Detecta incompatibilidades de tipos entre conexiones de flujo y genera
sugerencias de scripts puente para transformacion de datos.

Features:
- Matriz de compatibilidad de tipos
- Deteccion de conflictos de formato (fechas ES vs ISO)
- Puentes de archivo (ZIP -> PDF = descompresion)
- Generacion de atomos puente via Brain API
- Sugerencias semanticas por nombres similares
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List, Set, Union
from enum import Enum

from automatia_shared.contracts.ui_contract import InputType

logger = logging.getLogger(__name__)


# Extensiones de archivos comprimidos
COMPRESSED_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.tar.gz', '.tgz'}

# Extensiones de documentos
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt'}


@dataclass
class CoercionConfig:
    """Configuración para coerción de tipos."""
    strict: bool = False
    locale: str = "en_US"
    format_string: Optional[str] = None
    default_value: Any = None
    helper_functions: List[str] = field(default_factory=list)

@dataclass
class BridgeSuggestion:
    """Sugerencia de puente para transformacion de datos."""
    source_type: InputType
    target_type: InputType
    source_name: str = ""
    target_name: str = ""
    description: str = ""
    bridge_type: str = "type_conversion"  # type_conversion, file_extraction, format_conversion
    example_code: str = ""
    coercion_config: Optional[CoercionConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value if isinstance(self.source_type, InputType) else str(self.source_type),
            "target_type": self.target_type.value if isinstance(self.target_type, InputType) else str(self.target_type),
            "source_name": self.source_name,
            "target_name": self.target_name,
            "description": self.description,
            "bridge_type": self.bridge_type,
            "example_code": self.example_code,
            "coercion_config": self.coercion_config.__dict__ if self.coercion_config else None
        }


@dataclass
class TypeCompatibilityResult:
    """Resultado de validacion de compatibilidad de tipos."""
    is_compatible: bool
    error_message: Optional[str] = None
    bridge_suggestion: Optional[BridgeSuggestion] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_compatible": self.is_compatible,
            "error_message": self.error_message,
            "bridge_suggestion": self.bridge_suggestion.to_dict() if self.bridge_suggestion else None,
            "warnings": self.warnings
        }


class TypeCompatibilityService:
    """
    Servicio para validar compatibilidad de tipos entre conexiones de flujo.

    Detecta incompatibilidades y sugiere scripts puente para transformacion.
    """

    # Matriz de compatibilidad directa (sin necesidad de puente)
    # Clave: tipo origen, Valor: conjunto de tipos destino compatibles
    COMPATIBLE_TYPES: Dict[InputType, Set[InputType]] = {
        InputType.STR: {InputType.STR},
        InputType.INT: {InputType.INT, InputType.FLOAT},
        InputType.FLOAT: {InputType.INT, InputType.FLOAT},
        InputType.BOOL: {InputType.BOOL},
        InputType.DATE: {InputType.DATE, InputType.DATETIME},
        InputType.DATETIME: {InputType.DATE, InputType.DATETIME},
        InputType.FILE: {InputType.FILE},
        InputType.FILES: {InputType.FILES},
        InputType.SELECT: {InputType.SELECT, InputType.STR},  # SELECT es un STR con opciones
        InputType.SECRET: {InputType.SECRET, InputType.STR},  # SECRET es un STR enmascarado
        InputType.JSON: {InputType.JSON},
    }

    # Descripciones de puentes sugeridos
    BRIDGE_DESCRIPTIONS: Dict[Tuple[InputType, InputType], str] = {
        (InputType.STR, InputType.INT): "Convierte texto a numero entero. Limpia caracteres no numericos (moneda, separadores).",
        (InputType.STR, InputType.FLOAT): "Convierte texto a numero decimal. Maneja formatos de moneda y separadores regionales.",
        (InputType.STR, InputType.BOOL): "Convierte texto a booleano. Interpreta 'si/no', 'true/false', '1/0'.",
        (InputType.STR, InputType.DATE): "Parsea fecha desde texto. Detecta formatos comunes (DD/MM/YYYY, YYYY-MM-DD).",
        (InputType.STR, InputType.DATETIME): "Parsea fecha y hora desde texto.",
        (InputType.INT, InputType.STR): "Convierte numero entero a texto.",
        (InputType.FLOAT, InputType.STR): "Convierte numero decimal a texto con formato.",
        (InputType.BOOL, InputType.STR): "Convierte booleano a texto ('Si'/'No' o 'True'/'False').",
        (InputType.DATE, InputType.STR): "Formatea fecha como texto (configurable: DD/MM/YYYY, ISO, etc).",
        (InputType.DATETIME, InputType.STR): "Formatea fecha y hora como texto.",
        (InputType.JSON, InputType.STR): "Serializa objeto JSON a texto.",
        (InputType.STR, InputType.JSON): "Parsea texto JSON a objeto.",
        (InputType.FILES, InputType.FILE): "Selecciona un archivo de la lista (primero, por patron, etc).",
        (InputType.FILE, InputType.FILES): "Envuelve archivo en una lista.",
    }

    def _normalize_type(self, type_value: Union[InputType, str, None]) -> InputType:
        """
        Normaliza un valor de tipo a InputType.

        Args:
            type_value: Puede ser InputType, string o None

        Returns:
            InputType normalizado (STR por defecto si no se puede determinar)
        """
        if type_value is None:
            return InputType.STR

        if isinstance(type_value, InputType):
            return type_value

        if isinstance(type_value, str):
            # Intentar convertir string a InputType
            type_str = type_value.lower().strip()
            try:
                return InputType(type_str)
            except ValueError:
                # Mapeo de aliases comunes
                aliases = {
                    'string': InputType.STR,
                    'text': InputType.STR,
                    'integer': InputType.INT,
                    'number': InputType.INT,
                    'decimal': InputType.FLOAT,
                    'double': InputType.FLOAT,
                    'boolean': InputType.BOOL,
                    'path': InputType.FILE,
                    'files_list': InputType.FILES,
                    'object': InputType.JSON,
                    'dict': InputType.JSON,
                    'password': InputType.SECRET,
                    'dropdown': InputType.SELECT,
                }
                return aliases.get(type_str, InputType.STR)

        return InputType.STR

    def validate_connection(
        self,
        output_spec: Dict[str, Any],
        input_spec: Dict[str, Any]
    ) -> TypeCompatibilityResult:
        """
        Valida si dos campos son compatibles para conexion directa.

        Args:
            output_spec: Especificacion del campo de salida
                        {"name": str, "type": InputType, "extension"?: str, "format"?: str}
            input_spec: Especificacion del campo de entrada
                       {"name": str, "type": InputType, "extension"?: str, "format"?: str}

        Returns:
            TypeCompatibilityResult con el resultado de la validacion
        """
        source_type = self._normalize_type(output_spec.get("type"))
        target_type = self._normalize_type(input_spec.get("type"))
        source_name = output_spec.get("name", "origen")
        target_name = input_spec.get("name", "destino")

        # Verificar compatibilidad directa
        compatible_targets = self.COMPATIBLE_TYPES.get(source_type, set())

        if target_type in compatible_targets:
            # Tipos compatibles, pero verificar formatos si aplica
            return self._check_format_compatibility(
                output_spec, input_spec, source_type, target_type
            )

        # Tipos incompatibles - generar sugerencia de puente
        return self._generate_incompatibility_result(
            source_type, target_type, source_name, target_name,
            output_spec, input_spec
        )

    def validate_connection_simple(
        self,
        output_spec: Dict[str, Any],
        input_spec: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Version simplificada que retorna tupla (is_valid, error_msg).

        Mantiene compatibilidad con el formato del prompt original.
        """
        result = self.validate_connection(output_spec, input_spec)
        return (result.is_compatible, result.error_message)

    def _check_format_compatibility(
        self,
        output_spec: Dict[str, Any],
        input_spec: Dict[str, Any],
        source_type: InputType,
        target_type: InputType
    ) -> TypeCompatibilityResult:
        """
        Verifica compatibilidad de formatos para tipos compatibles.

        Por ejemplo, fechas con diferentes formatos o archivos con diferentes extensiones.
        """
        warnings = []

        # Verificar formatos de fecha
        if source_type in {InputType.DATE, InputType.DATETIME}:
            source_format = output_spec.get("format")
            target_format = input_spec.get("format")

            if source_format and target_format and source_format != target_format:
                # Formatos diferentes requieren conversion
                return TypeCompatibilityResult(
                    is_compatible=False,
                    error_message=f"Formatos de fecha incompatibles: {source_format} -> {target_format}",
                    bridge_suggestion=BridgeSuggestion(
                        source_type=source_type,
                        target_type=target_type,
                        source_name=output_spec.get("name", ""),
                        target_name=input_spec.get("name", ""),
                        description=f"Convierte formato de fecha de {source_format} a {target_format}",
                        bridge_type="format_conversion"
                    )
                )

        # Verificar extensiones de archivo
        if source_type == InputType.FILE:
            source_ext = output_spec.get("extension", "").lower()
            target_ext = input_spec.get("extension", "").lower()

            if source_ext and target_ext and source_ext != target_ext:
                return self._check_file_extension_compatibility(
                    source_ext, target_ext, output_spec, input_spec
                )

        return TypeCompatibilityResult(
            is_compatible=True,
            warnings=warnings
        )

    def _check_file_extension_compatibility(
        self,
        source_ext: str,
        target_ext: str,
        output_spec: Dict[str, Any],
        input_spec: Dict[str, Any]
    ) -> TypeCompatibilityResult:
        """Verifica compatibilidad de extensiones de archivo."""

        # Caso especial: archivos comprimidos a documentos
        if source_ext in COMPRESSED_EXTENSIONS and target_ext in DOCUMENT_EXTENSIONS:
            return TypeCompatibilityResult(
                is_compatible=False,
                error_message=f"Archivo comprimido ({source_ext}) requiere extraccion para {target_ext}",
                bridge_suggestion=BridgeSuggestion(
                    source_type=InputType.FILE,
                    target_type=InputType.FILE,
                    source_name=output_spec.get("name", ""),
                    target_name=input_spec.get("name", ""),
                    description=f"Puente de descompresion: extrae {target_ext} de archivo {source_ext}",
                    bridge_type="file_extraction"
                )
            )

        # Extensiones diferentes pero no critico
        return TypeCompatibilityResult(
            is_compatible=False,
            error_message=f"Extension de archivo diferente: {source_ext} -> {target_ext}",
            bridge_suggestion=BridgeSuggestion(
                source_type=InputType.FILE,
                target_type=InputType.FILE,
                source_name=output_spec.get("name", ""),
                target_name=input_spec.get("name", ""),
                description=f"Convierte archivo de {source_ext} a {target_ext}",
                bridge_type="file_conversion"
            )
        )

    def _generate_incompatibility_result(
        self,
        source_type: InputType,
        target_type: InputType,
        source_name: str,
        target_name: str,
        output_spec: Dict[str, Any],
        input_spec: Dict[str, Any]
    ) -> TypeCompatibilityResult:
        """Genera resultado de incompatibilidad con sugerencia de puente."""

        # Obtener descripcion predefinida o generar una generica
        description = self.BRIDGE_DESCRIPTIONS.get(
            (source_type, target_type),
            f"Transforma {source_type.value} a {target_type.value}"
        )

        return TypeCompatibilityResult(
            is_compatible=False,
            error_message=f"Tipos incompatibles: {source_type.value} no es directamente compatible con {target_type.value}",
            bridge_suggestion=BridgeSuggestion(
                source_type=source_type,
                target_type=target_type,
                source_name=source_name,
                target_name=target_name,
                description=description,
                bridge_type="type_conversion"
            )
        )

    async def request_bridge_script(
        self,
        source_type: InputType,
        target_type: InputType,
        source_name: str = "input_value",
        target_name: str = "output_value",
        example_value: Optional[str] = None,
        license_key: str = "TRIAL-KEY"
    ) -> str:
        """
        Solicita al Brain generar un script puente para la conversion.
        Delegates to BridgeGenerationService.

        Args:
            source_type: Tipo de dato de origen
            target_type: Tipo de dato de destino
            source_name: Nombre del campo de origen
            target_name: Nombre del campo de destino
            example_value: Valor de ejemplo para guiar la conversion
            license_key: Clave de licencia (unused by local service but kept for interface)

        Returns:
            Codigo Python del script puente
        """
        try:
            from client_app.app.services.bridge_generation_service import bridge_generation_service
            
            # Prepare context for the service
            context = {
                "source_name": source_name,
                "target_name": target_name,
            }
            if example_value:
                context["examples"] = [example_value]

            code = await bridge_generation_service.generate_bridge_code(
                source_type=source_type.value if isinstance(source_type, InputType) else str(source_type),
                target_type=target_type.value if isinstance(target_type, InputType) else str(target_type),
                context=context
            )
            return code
        except Exception as e:
            logger.error(f"Error solicitando script puente al Brain: {e}")
            # Fallback: generar codigo basico
            return self._generate_fallback_bridge_code(
                source_type, target_type, source_name, target_name
            )

    def _generate_fallback_bridge_code(
        self,
        source_type: InputType,
        target_type: InputType,
        source_name: str,
        target_name: str
    ) -> str:
        """Genera codigo puente basico como fallback si Brain no disponible."""

        conversions = {
            (InputType.STR, InputType.INT): f"""
def transform({source_name}):
    \"\"\"Convierte texto a entero.\"\"\"
    # Limpiar caracteres no numericos
    cleaned = ''.join(c for c in str({source_name}) if c.isdigit() or c == '-')
    return int(cleaned) if cleaned else 0
""",
            (InputType.STR, InputType.FLOAT): f"""
def transform({source_name}):
    \"\"\"Convierte texto a decimal.\"\"\"
    # Manejar formato europeo (1.234,56) y americano (1,234.56)
    text = str({source_name}).replace(' ', '').replace('€', '').replace('$', '')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')
    return float(text) if text else 0.0
""",
            (InputType.STR, InputType.BOOL): f"""
def transform({source_name}):
    \"\"\"Convierte texto a booleano.\"\"\"
    text = str({source_name}).lower().strip()
    return text in ('true', '1', 'yes', 'si', 'sí', 'on', 'activo')
""",
            (InputType.BOOL, InputType.STR): f"""
def transform({source_name}):
    \"\"\"Convierte booleano a texto.\"\"\"
    return 'Si' if {source_name} else 'No'
""",
            (InputType.INT, InputType.STR): f"""
def transform({source_name}):
    \"\"\"Convierte entero a texto.\"\"\"
    return str({source_name})
""",
            (InputType.FLOAT, InputType.STR): f"""
def transform({source_name}):
    \"\"\"Convierte decimal a texto con 2 decimales.\"\"\"
    return f'{{{{source_name}}:.2f}}'
""",
        }

        key = (source_type, target_type)
        if key in conversions:
            return conversions[key]

        # Conversion generica con mejor esfuerzo
        return f"""
def transform({source_name}):
    \"\"\"Puente de conversion generico {source_type.value} -> {target_type.value}.\"\"\"
    try:
        # Intento basico de conversion a texto si el destino es texto
        if "{target_type}" == "string":
            try:
                import json
                if isinstance({source_name}, (dict, list)):
                    return json.dumps({source_name}, ensure_ascii=False)
            except:
                pass
            return str({source_name})
            
        # Para otros tipos, devolvemos el valor original esperando compatibilidad
        return {source_name}
    except Exception:
        # Fallback de seguridad
        return {source_name}
"""

    async def create_bridge_atom(
        self,
        source_type: InputType,
        target_type: InputType,
        source_name: str,
        target_name: str,
        example_value: Optional[str] = None,
        license_key: str = "TRIAL-KEY"
    ) -> Any:
        """
        Crea un atomo puente en la biblioteca de scripts.

        El atomo se marca con is_bridge=True para no ensuciar
        el catalogo principal del usuario.

        Args:
            source_type: Tipo de origen
            target_type: Tipo de destino
            source_name: Nombre del campo origen
            target_name: Nombre del campo destino
            example_value: Valor de ejemplo
            license_key: Clave de licencia

        Returns:
            ScriptLibrary object del atomo creado
        """
        # Generar codigo del puente
        code = await self.request_bridge_script(
            source_type=source_type,
            target_type=target_type,
            source_name=source_name,
            target_name=target_name,
            example_value=example_value,
            license_key=license_key
        )

        # Crear el atomo en la biblioteca
        from client_app.app.services.script_library_service import script_library_service

        bridge_name = f"Puente: {source_type.value} -> {target_type.value}"
        description = f"Convierte {source_name} ({source_type.value}) a {target_name} ({target_type.value})"

        atom = await script_library_service.add_script(
            source_module='bridge',
            name=bridge_name,
            code=code,
            description=description,
            tags=['puente', 'auto-generado', 'conversion'],
            is_bridge=True,
            source_metadata={
                'is_bridge': True,
                'auto_generated': True,
                'source_type': source_type.value,
                'target_type': target_type.value,
                'source_name': source_name,
                'target_name': target_name
            },
            ui_contract={
                'inputs': [
                    {'name': source_name, 'type': source_type.value, 'label': source_name.replace('_', ' ').title()}
                ],
                'outputs': [
                    {'name': target_name, 'type': target_type.value, 'label': target_name.replace('_', ' ').title()}
                ]
            }
        )

        return atom

    def coerce_value(
        self,
        value: Any,
        target_type: Union[InputType, str],
        config: Optional[CoercionConfig] = None
    ) -> Any:
        """
        Intenta convertir un valor al tipo de destino especificado.

        Args:
            value: Valor a convertir
            target_type: Tipo de destino (InputType o str)
            config: Configuración opcional para la conversión

        Returns:
            Valor convertido o el valor original si no se puede convertir
        """
        target = self._normalize_type(target_type)
        if value is None:
            return config.default_value if config else None

        # Si ya es del tipo deseado, retornar
        if isinstance(value, str) and target == InputType.STR: return value
        if isinstance(value, int) and target == InputType.INT: return value
        if isinstance(value, float) and target == InputType.FLOAT: return value
        if isinstance(value, bool) and target == InputType.BOOL: return value

        try:
            if target == InputType.STR:
                if isinstance(value, (dict, list)):
                    import json
                    return json.dumps(value, ensure_ascii=False)
                return str(value)

            if target == InputType.INT:
                if isinstance(value, str):
                    # Limpiar caracteres no numéricos
                    cleaned = "".join(c for c in value if c.isdigit() or c == '-')
                    return int(cleaned) if cleaned else 0
                return int(float(value))

            if target == InputType.FLOAT:
                if isinstance(value, str):
                    # Manejar formatos regionales básicos
                    cleaned = value.replace(",", ".")
                    if cleaned.count(".") > 1: # Formato 1.234.567,89
                        cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
                    return float(cleaned)
                return float(value)

            if target == InputType.BOOL:
                if isinstance(value, str):
                    val = value.lower().strip()
                    return val in ("true", "1", "yes", "si", "sí", "on", "activo")
                return bool(value)

            if target == InputType.JSON:
                if isinstance(value, str):
                    import json
                    return json.loads(value)
                return value # Asumimos que ya es un objeto compatible

            if target == InputType.DATE:
                from datetime import datetime
                if isinstance(value, str):
                    # Intentar formatos comunes
                    formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt).date()
                        except ValueError:
                            continue
                return value

        except Exception as e:
            logger.warning(f"Error en coerción de valor '{value}' a {target}: {e}")
            if config and config.strict:
                raise e

        return value

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calcula la similitud semantica entre dos nombres de campos.

        Util para sugerir conexiones automaticas entre campos
        con nombres relacionados.

        Args:
            name1: Primer nombre
            name2: Segundo nombre

        Returns:
            Puntuacion de similitud (0.0 a 1.0)
        """
        # Normalizar nombres
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        # Calcular similitud de Jaccard sobre palabras
        words1 = set(n1.split('_'))
        words2 = set(n2.split('_'))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        jaccard = intersection / union if union > 0 else 0.0

        # Bonus por sinonimos comunes
        synonyms = {
            frozenset({'precio', 'coste', 'importe', 'total', 'valor'}),
            frozenset({'fecha', 'date', 'dia', 'tiempo'}),
            frozenset({'nombre', 'name', 'titulo'}),
            frozenset({'id', 'identificador', 'codigo', 'numero'}),
            frozenset({'email', 'correo', 'mail'}),
        }

        for syn_group in synonyms:
            if (words1 & syn_group) and (words2 & syn_group):
                jaccard += 0.3
                break

        return min(jaccard, 1.0)

    def _normalize_name(self, name: str) -> str:
        """Normaliza un nombre de campo para comparacion."""
        # Convertir camelCase a snake_case
        name = re.sub(r'([A-Z])', r'_\1', name).lower()
        # Limpiar caracteres especiales
        name = re.sub(r'[^a-z0-9_]', '_', name)
        # Eliminar underscores multiples
        name = re.sub(r'_+', '_', name).strip('_')
        return name

    def suggest_connections(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Sugiere conexiones automaticas basadas en nombres y tipos.

        Args:
            outputs: Lista de campos de salida disponibles
            inputs: Lista de campos de entrada requeridos
            min_similarity: Umbral minimo de similitud para sugerir

        Returns:
            Lista de sugerencias de conexion
        """
        suggestions = []

        for output in outputs:
            for input_field in inputs:
                # Calcular similitud de nombre
                name_sim = self.calculate_name_similarity(
                    output.get("name", ""),
                    input_field.get("name", "")
                )

                # Verificar compatibilidad de tipo
                result = self.validate_connection(output, input_field)

                # Solo sugerir si hay similitud de nombre suficiente
                if name_sim >= min_similarity:
                    suggestions.append({
                        "source": output,
                        "target": input_field,
                        "name_similarity": name_sim,
                        "type_compatible": result.is_compatible,
                        "needs_bridge": not result.is_compatible,
                        "bridge_suggestion": result.bridge_suggestion.to_dict() if result.bridge_suggestion else None
                    })

        # Ordenar por similitud de nombre
        suggestions.sort(key=lambda x: x["name_similarity"], reverse=True)

        return suggestions


# Singleton instance
type_compatibility_service = TypeCompatibilityService()
