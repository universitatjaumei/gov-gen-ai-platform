from enum import Enum
from typing import List, Optional, Any, Dict, Union, Pattern
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import os
from pathlib import Path
from decimal import Decimal
import re
from datetime import datetime, date

class InputType(str, Enum):
    """
    Tipos de datos soportados para entradas de scripts y workflows.
    Prompt 2A.
    """
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    FILE = "file"      # Single file path
    FILES = "files"    # List of file paths
    SELECT = "select"  # Dropdown selection
    SECRET = "secret"  # Password/API Key (masked)
    JSON = "json"      # Raw JSON object
    DATE = "date"
    DATETIME = "datetime"

# --- Advanced Models (Prompt 2B) ---

class Constraints(BaseModel):
    """
    Restricciones de validación para un campo de entrada (mínimo, máximo, regex, etc.).
    """
    min: Optional[float] = None
    max: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex: Optional[str] = None
    enum: Optional[List[Any]] = None

class DependencyOperator(str, Enum):
    """
    Operadores lógicos para evaluar dependencias entre campos.
    """
    EQ = "=="
    NEQ = "!="
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"

class DependencyCondition(BaseModel):
    """
    Condición que debe cumplirse para activar una acción de dependencia.
    """
    field: str
    operator: DependencyOperator
    value: Optional[Any] = None

class DependencyAction(BaseModel):
    """
    Acción a ejecutar (cambiar visibilidad, obligatoriedad, etc.) cuando se cumple una condición.
    """
    required: Optional[bool] = None
    visible: Optional[bool] = None
    enable: Optional[bool] = None
    set_default: Optional[Any] = None

class Dependency(BaseModel):
    """
    Representa una relación de dependencia completa: Si [condición] entonces [acción].
    """
    model_config = ConfigDict(populate_by_name=True)
    condition: DependencyCondition = Field(alias="if")
    action: DependencyAction = Field(alias="then")

class PythonType(str, Enum):
    """
    Tipos de datos nativos de Python para la coerción final tras la validación de UI.
    """
    STR = "str"
    INT = "int"
    FLOAT = "float"
    DECIMAL = "Decimal"
    BOOL = "bool"
    PATH = "Path"
    DATE = "date"
    DATETIME = "datetime"
    DATAFRAME = "DataFrame"

class CoercionConfig(BaseModel):
    """
    Configuración opcional para forzar la conversión de un dato a un tipo específico de Python.
    """
    python_type: PythonType
    format_hint: Optional[str] = None

# -----------------------------------

class InputDefinition(BaseModel):
    """
    Definición de un campo de entrada para la UI.
    """
    name: str = Field(..., description="Identificador unico de la variable (snake_case)")
    label: str = Field(..., description="Etiqueta visible para el usuario")
    type: InputType = Field(..., description="Tipo de dato")
    required: bool = Field(default=True, description="Si es obligatorio")
    description: Optional[str] = Field(default=None, description="Tooltip o ayuda")
    default: Optional[Any] = Field(default=None, description="Valor por defecto")
    options: Optional[List[str]] = Field(default=None, description="Opciones para tipo SELECT")
    
    # Advanced 2B
    constraints: Optional[Constraints] = None
    dependencies: Optional[List[Dependency]] = None
    coercion: Optional[CoercionConfig] = None
    
    # i18n
    label_i18n_key: Optional[str] = None
    helper_text: Optional[str] = None
    helper_i18n_key: Optional[str] = None

    @field_validator('name')
    def validate_name(cls, v):
        """
        Valida que el nombre de la variable sea un identificador válido de Python.
        """
        if not v.isidentifier():
            raise ValueError(f"El nombre '{v}' debe ser un identificador valido (snake_case recomendado)")
        return v

    @model_validator(mode='after')
    def validate_options(self):
        """
        Valida que si el tipo es SELECT, se hayan definido opciones.
        """
        if self.type == InputType.SELECT and not self.options:
            raise ValueError("El tipo SELECT requiere definir 'options'")
        return self

class UIContract(BaseModel):
    """
    Contrato que define las entradas esperadas por un script o automatismo.
    """
    inputs: List[InputDefinition] = Field(default_factory=list)
    version: str = Field(default="1.0.0")

    def _evaluate_dependency(self, dep: Dependency, data: Dict[str, Any]) -> bool:
        """Evalua si una dependencia se cumple"""
        field_val = data.get(dep.condition.field)
        op = dep.condition.operator
        target = dep.condition.value

        if op == DependencyOperator.EXISTS:
            return field_val is not None and field_val != ""
        
        if op == DependencyOperator.NOT_EXISTS:
            return field_val is None or field_val == ""

        # Si el campo no existe y no es check de existencia, es falso (salvo lógica custom)
        if field_val is None: 
            return False

        if op == DependencyOperator.EQ: return field_val == target
        if op == DependencyOperator.NEQ: return field_val != target
        if op == DependencyOperator.IN: return field_val in (target if isinstance(target, list) else [])
        if op == DependencyOperator.NOT_IN: return field_val not in (target if isinstance(target, list) else [])
        
        return False

    def validate_inputs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida un diccionario de entradas contra el contrato.
        Realiza conversión de tipos y validación avanzada.
        """
        validated = {}
        errors = []

        # First pass: Basic Typos & Raw Values (needed for dependency check)
        # We need raw data to evaluate dependencies first?
        # Let's process in order.
        
        # Helper to get effective state (is required? is visible?)
        effective_defs = {}
        for inp in self.inputs:
            eff = {
                "required": inp.required,
                "visible": True,
                "default": inp.default
            }
            # Evaluate dependencies
            if inp.dependencies:
                for dep in inp.dependencies:
                    if self._evaluate_dependency(dep, data):
                        if dep.action.required is not None: eff["required"] = dep.action.required
                        if dep.action.visible is not None: eff["visible"] = dep.action.visible
                        if dep.action.set_default is not None: eff["default"] = dep.action.set_default
            
            effective_defs[inp.name] = eff

        
        for input_def in self.inputs:
            eff = effective_defs[input_def.name]
            
            # Skip validation if invisible?
            if not eff["visible"]:
                # Should we clear value? Or keep validation?
                # Usually invisible means "not active", so we don't validate unless we want hidden state.
                # Let's assume we don't return it in validated output if invisible.
                continue

            value = data.get(input_def.name)

            # 1. Required Check
            if value is None or value == "":
                if eff["required"]:
                    if eff["default"] is not None:
                        value = eff["default"] # Apply default
                    else:
                        errors.append(f"Campo requerido faltante: {input_def.name}")
                        continue
                else:
                    # Optional and empty -> None or default
                    validated[input_def.name] = eff["default"]
                    continue
            
            # 2. Type Conversion (Basic)
            try:
                converted_value = value # Interim
                
                if input_def.type in [InputType.STR, InputType.SECRET, InputType.SELECT]:
                    converted_value = str(value)
                    if input_def.type == InputType.SELECT and converted_value not in (input_def.options or []):
                         errors.append(f"Valor '{converted_value}' no valido para {input_def.name}. Opciones: {input_def.options}")

                elif input_def.type == InputType.INT:
                    converted_value = int(value)

                elif input_def.type == InputType.FLOAT:
                    converted_value = float(value)

                elif input_def.type == InputType.BOOL:
                    if isinstance(value, bool): converted_value = value
                    elif str(value).lower() in ('true', '1', 'yes', 'on'): converted_value = True
                    else: converted_value = False

                elif input_def.type == InputType.FILE:
                    converted_value = str(value)

                elif input_def.type == InputType.FILES:
                    if isinstance(value, str):
                        if ',' in value: converted_value = [x.strip() for x in value.split(',')]
                        else: converted_value = [value]
                    elif isinstance(value, list):
                        converted_value = [str(x) for x in value]
                    else:
                        errors.append(f"Formato invalido para FILES en {input_def.name}")
                        continue

                elif input_def.type == InputType.JSON:
                    if isinstance(value, (dict, list)): converted_value = value
                    elif isinstance(value, str):
                        import json
                        try:
                            converted_value = json.loads(value)
                        except:
                             errors.append(f"JSON invalido en {input_def.name}")
                             continue

                # 3. Constraints Validation
                if input_def.constraints:
                    c = input_def.constraints
                    
                    # Numeric
                    if isinstance(converted_value, (int, float)):
                        if c.min is not None and converted_value < c.min:
                            errors.append(f"{input_def.name}: Valor {converted_value} menor al minimo {c.min}")
                        if c.max is not None and converted_value > c.max:
                            errors.append(f"{input_def.name}: Valor {converted_value} mayor al maximo {c.max}")
                    
                    # String / Sequence
                    if hasattr(converted_value, '__len__'):
                        if c.min_length is not None and len(converted_value) < c.min_length:
                            errors.append(f"{input_def.name}: Longitud menor a {c.min_length}")
                        if c.max_length is not None and len(converted_value) > c.max_length:
                             errors.append(f"{input_def.name}: Longitud mayor a {c.max_length}")
                    
                    # Regex
                    if isinstance(converted_value, str) and c.regex:
                        if not re.match(c.regex, converted_value):
                            errors.append(f"{input_def.name}: Formato no valido (regex)")
                            
                    # Enum
                    if c.enum and converted_value not in c.enum:
                         errors.append(f"{input_def.name}: Valor no permitido")

                # 4. Final Python Coercion
                final_val = converted_value
                if input_def.coercion:
                    ptype = input_def.coercion.python_type
                    try:
                        if ptype == PythonType.DECIMAL:
                            final_val = Decimal(str(converted_value))
                        elif ptype == PythonType.PATH:
                            final_val = Path(converted_value)
                        # Add more coercions as needed
                    except Exception as e:
                        errors.append(f"Error de coercion en {input_def.name}: {e}")

                validated[input_def.name] = final_val

            except ValueError:
                errors.append(f"Error de tipo en {input_def.name}: se esperaba {input_def.type.value}")

        if errors:
            raise ValueError(f"Errores de validacion: {'; '.join(errors)}")

        return validated

    def to_schema(self) -> Dict[str, Any]:
        """
        Genera un JSON Schema enriquecido con constraints.
        """
        properties = {}
        required = []

        for inp in self.inputs:
            field_schema = {
                "title": inp.label_i18n_key or inp.label,
                "description": inp.helper_text or inp.description,
                "default": inp.default
            }
            
            # Map Types
            if inp.type == InputType.STR: field_schema["type"] = "string"
            elif inp.type == InputType.INT: field_schema["type"] = "integer"
            elif inp.type == InputType.FLOAT: field_schema["type"] = "number"
            elif inp.type == InputType.BOOL: field_schema["type"] = "boolean"
            elif inp.type == InputType.SELECT: 
                field_schema["type"] = "string"
                field_schema["enum"] = inp.options
            elif inp.type == InputType.FILE:
                field_schema["type"] = "string"
                field_schema["format"] = "file-path"
            elif inp.type == InputType.DATE:
                field_schema["type"] = "string"
                field_schema["format"] = "date"
            elif inp.type == InputType.DATETIME:
                field_schema["type"] = "string"
                field_schema["format"] = "date-time"
            elif inp.type == InputType.JSON:
                field_schema["type"] = "object"
            else:
                field_schema["type"] = "string"

            # Map Constraints
            if inp.constraints:
                c = inp.constraints
                if c.min is not None: field_schema["minimum"] = c.min
                if c.max is not None: field_schema["maximum"] = c.max
                if c.min_length is not None: field_schema["minLength"] = c.min_length
                if c.max_length is not None: field_schema["maxLength"] = c.max_length
                if c.regex is not None: field_schema["pattern"] = c.regex
            
            properties[inp.name] = field_schema
            if inp.required:
                required.append(inp.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


class OutputField(BaseModel):
    """
    Definición de un campo de salida producido por un átomo.
    Simétrico a InputDefinition pero para outputs.
    """
    name: str = Field(..., description="Identificador único del campo (snake_case)")
    label: str = Field(..., description="Etiqueta descriptiva")
    type: InputType = Field(..., description="Tipo de dato producido")
    description: Optional[str] = Field(default=None)
    nullable: bool = Field(default=False, description="Si el campo puede ser None")

    # Constraints de salida (garantías que ofrece el átomo)
    constraints: Optional[Constraints] = None

    # Ejemplo de valor típico (para documentación y testing)
    example: Optional[Any] = None


class OutputSchema(BaseModel):
    """
    Contrato de salida de un átomo o script.
    Define qué datos produce y con qué garantías.
    """
    fields: List[OutputField] = Field(default_factory=list)
    version: str = Field(default="1.0.0")

    # Metadata adicional
    is_streaming: bool = Field(default=False, description="Si produce datos incrementalmente")
    produces_multiple: bool = Field(default=False, description="Si retorna lista de registros")

    def to_json_schema(self) -> Dict[str, Any]:
        """Genera JSON Schema para validación de salidas."""
        properties = {}
        required = []

        for field in self.fields:
            field_schema = {"description": field.description}

            # Map types
            type_map = {
                InputType.STR: "string",
                InputType.INT: "integer",
                InputType.FLOAT: "number",
                InputType.BOOL: "boolean",
                InputType.JSON: "object",
                InputType.DATE: "string",
                InputType.DATETIME: "string",
            }
            field_schema["type"] = type_map.get(field.type, "string")

            if field.constraints:
                if field.constraints.min is not None:
                    field_schema["minimum"] = field.constraints.min
                if field.constraints.max is not None:
                    field_schema["maximum"] = field.constraints.max
                if field.constraints.regex:
                    field_schema["pattern"] = field.constraints.regex

            properties[field.name] = field_schema
            if not field.nullable:
                required.append(field.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


class DataContract(BaseModel):
    """
    Contrato completo de un átomo: entradas + salidas.
    Usado para validación de conexiones en el editor de flujos.
    """
    inputs: UIContract = Field(default_factory=UIContract)
    outputs: OutputSchema = Field(default_factory=OutputSchema)
    version: str = Field(default="1.0.0")
    description: Optional[str] = Field(default=None, description="Descripción funcional del activo")


__all__ = [
    "InputType",
    "Constraints",
    "DependencyOperator",
    "DependencyCondition",
    "DependencyAction",
    "Dependency",
    "PythonType",
    "CoercionConfig",
    "InputDefinition",
    "UIContract",
    "OutputField",
    "OutputSchema",
    "DataContract",
]
