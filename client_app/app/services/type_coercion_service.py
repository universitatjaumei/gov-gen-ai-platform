
from typing import Any, List, Dict, Union
import json
from automatia_shared.enums import InputType

class TypeCoercionService:
    """
    Servicio centralizado para la coerción de tipos de entrada.
    Asegura que los datos recibidos (generalmente strings de UI/JSON)
    se conviertan al tipo esperado por la lógica de negocio.
    """

    @staticmethod
    def coerce(value: Any, target_type: Union[InputType, str, None]) -> Any:
        # Si no hay tipo o valor es None (y tipo no es string que espera ""), retornar tal cual
        if not target_type:
            return value

        # Normalizar target_type a string si es Enum
        t_type = target_type.value if isinstance(target_type, InputType) else target_type

        # Handlers por tipo
        if t_type == InputType.STRING:
            return str(value) if value is not None else ""
        
        if t_type == InputType.INTEGER:
            try:
                return int(float(value)) if isinstance(value, (str, float)) else int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot coerce '{value}' to Integer")

        if t_type == InputType.FLOAT:
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot coerce '{value}' to Float")

        if t_type == InputType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                v_lower = value.lower().strip()
                if v_lower in ("true", "1", "yes", "on"):
                    return True
                if v_lower in ("false", "0", "no", "off", ""):
                    return False
                # Default for unknown strings could vary, let's strict fail or default false?
                # Test implies specific falsy list. Let's stick to False for anything else usually? 
                # Actually, standard bool("random") is True. Let's be explicit based on test.
                # Test covers: true, True, TRUE, 1, yes, on -> True
                # false, False, FALSE, 0, no, off, "" -> False
                # If checking logic above, we cover the True/False sets clearly.
                return False 
            return bool(value)

        if t_type == InputType.LIST:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                s_val = value.strip()
                if s_val.startswith("[") and s_val.endswith("]"):
                    try:
                        return json.loads(s_val)
                    except json.JSONDecodeError:
                        # Fallback to comma split if JSON fails?
                        # Or just fail? Let's assume list logic:
                        # Test says "a,b,c" -> ["a", "b", "c"]
                        # Test says '["x", "y"]' -> ["x", "y"]
                        pass 
                # Comma separated
                return [x.strip() for x in value.split(",") if x.strip()]
            return [value]

        if t_type == InputType.DICT:
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Cannot coerce string to Dict: Invalid JSON")
            raise ValueError(f"Cannot coerce {type(value)} to Dict")

        return value
