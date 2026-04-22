"""
Tests TDD para el motor de inferencia de contratos atomicos.
Prompt #1: Motor de Inferencia de Contratos Atomicos (Capa Shared)
Prompt #5: Motor de Inferencia de Esquemas JSON (Capa Shared)
"""
import pytest
from automatia_shared.utils.inference import infer_contract_from_source, infer_contract_from_json
from automatia_shared.contracts.ui_contract import UIContract, InputType


def test_infer_contract_basic_script():
    """Test basico: detectar variables {{var}} en codigo fuente."""
    source_code = """
    # Script de prueba
    cliente = "{{nombre_cliente}}"
    monto = {{ importe_total }}
    fecha = "{{ fecha_vencimiento }}"
    # Re-uso de variable para probar deduplicacion
    print(f"Procesando {cliente}...")
    """

    contract = infer_contract_from_source(source_code)

    assert isinstance(contract, UIContract)
    # Verificar que hay 3 inputs unicos
    assert len(contract.inputs) == 3

    # Verificar nombres
    input_names = [i.name for i in contract.inputs]
    assert "nombre_cliente" in input_names
    assert "importe_total" in input_names
    assert "fecha_vencimiento" in input_names

    # Verificar tipos por defecto (STR es el tipo string del enum)
    for inp in contract.inputs:
        assert inp.type == InputType.STR


def test_infer_contract_empty_source():
    """Test con codigo sin variables: debe devolver contrato vacio."""
    contract = infer_contract_from_source("print('hola')")
    assert len(contract.inputs) == 0


def test_infer_contract_deduplication():
    """Test de deduplicacion: variables repetidas solo aparecen una vez."""
    source_code = """
    x = "{{var1}}"
    y = "{{var1}}"
    z = "{{var1}}"
    """
    contract = infer_contract_from_source(source_code)
    assert len(contract.inputs) == 1
    assert contract.inputs[0].name == "var1"


def test_infer_contract_preserves_order():
    """Test de orden: los inputs deben aparecer en orden de aparicion."""
    source_code = """
    a = "{{primera}}"
    b = "{{segunda}}"
    c = "{{tercera}}"
    """
    contract = infer_contract_from_source(source_code)
    names = [i.name for i in contract.inputs]
    assert names == ["primera", "segunda", "tercera"]


def test_infer_contract_label_humanization():
    """Test de humanizacion: snake_case se convierte a Title Case."""
    source_code = "x = '{{nombre_del_cliente}}'"
    contract = infer_contract_from_source(source_code)
    assert contract.inputs[0].label == "Nombre Del Cliente"


def test_infer_contract_ignores_invalid_names():
    """Test de validacion: ignora patrones que no son identificadores validos."""
    source_code = """
    a = "{{valid_name}}"
    b = "{{123_invalid}}"
    c = "{{also-invalid}}"
    d = "{{ }}"
    """
    contract = infer_contract_from_source(source_code)
    # Solo 'valid_name' es un identificador Python valido
    assert len(contract.inputs) == 1
    assert contract.inputs[0].name == "valid_name"


def test_infer_contract_handles_none():
    """Test de robustez: manejar None sin excepcion."""
    contract = infer_contract_from_source(None)
    assert isinstance(contract, UIContract)
    assert len(contract.inputs) == 0


def test_infer_contract_handles_empty_string():
    """Test de robustez: manejar string vacio sin excepcion."""
    contract = infer_contract_from_source("")
    assert isinstance(contract, UIContract)
    assert len(contract.inputs) == 0


def test_infer_contract_whitespace_in_braces():
    """Test de limpieza: espacios dentro de las llaves se ignoran."""
    source_code = """
    a = "{{   variable_con_espacios   }}"
    b = "{{sin_espacios}}"
    """
    contract = infer_contract_from_source(source_code)
    names = [i.name for i in contract.inputs]
    assert "variable_con_espacios" in names
    assert "sin_espacios" in names


# =============================================================================
# Prompt #5: Tests para inferencia desde JSON
# =============================================================================

def test_infer_contract_from_simple_json():
    """Test basico: inferir contrato desde JSON simple."""
    sample_json = {
        "id": 101,
        "nombre_producto": "Laptop Pro",
        "esta_activo": True,
        "precio": 1200.50
    }

    contract = infer_contract_from_json(sample_json)

    # Validar que se detectaron los 4 campos
    assert len(contract.inputs) == 4

    names = [i.name for i in contract.inputs]
    assert "id" in names
    assert "nombre_producto" in names
    assert "esta_activo" in names
    assert "precio" in names

    # Verificar tipos correctos
    for inp in contract.inputs:
        if inp.name == "id":
            assert inp.type == InputType.INT
        elif inp.name == "esta_activo":
            assert inp.type == InputType.BOOL
        elif inp.name == "precio":
            assert inp.type == InputType.FLOAT
        elif inp.name == "nombre_producto":
            assert inp.type == InputType.STR


def test_infer_contract_from_nested_json():
    """Test de aplanamiento: JSON anidado genera llaves con guion bajo (identifier valido)."""
    sample_nested = {
        "pedido": {
            "nro": "FAC-001",
            "cliente": {"nombre": "Juan"}
        }
    }

    contract = infer_contract_from_json(sample_nested)

    # Validar aplanamiento con guiones bajos (requerido por InputDefinition)
    names = [i.name for i in contract.inputs]
    assert "pedido_nro" in names
    assert "pedido_cliente_nombre" in names


def test_infer_contract_from_json_string():
    """Test: aceptar string JSON y parsearlo."""
    json_str = '{"campo1": "valor", "campo2": 42}'
    contract = infer_contract_from_json(json_str)

    names = [i.name for i in contract.inputs]
    assert "campo1" in names
    assert "campo2" in names


def test_infer_contract_from_json_list():
    """Test: lista de objetos toma el primer elemento para inferir esquema."""
    sample_list = [
        {"id": 1, "nombre": "Item 1"},
        {"id": 2, "nombre": "Item 2"}
    ]

    contract = infer_contract_from_json(sample_list)

    names = [i.name for i in contract.inputs]
    assert "id" in names
    assert "nombre" in names
    assert len(contract.inputs) == 2


def test_infer_contract_from_json_empty():
    """Test: JSON vacio devuelve contrato vacio."""
    contract = infer_contract_from_json({})
    assert len(contract.inputs) == 0


def test_infer_contract_from_json_none():
    """Test de robustez: None devuelve contrato vacio."""
    contract = infer_contract_from_json(None)
    assert isinstance(contract, UIContract)
    assert len(contract.inputs) == 0


def test_infer_contract_from_json_with_null_values():
    """Test: valores None se mapean a STR por defecto."""
    sample = {"campo_nulo": None, "campo_texto": "valor"}
    contract = infer_contract_from_json(sample)

    for inp in contract.inputs:
        if inp.name == "campo_nulo":
            assert inp.type == InputType.STR


def test_infer_contract_from_json_label_humanization():
    """Test: labels se humanizan desde snake_case y dot notation."""
    sample = {"user_id": 1}
    contract = infer_contract_from_json(sample)

    assert contract.inputs[0].label == "User Id"


def test_infer_contract_from_json_date_detection():
    """Test: strings con formato fecha se detectan como DATE."""
    sample = {
        "fecha_creacion": "2024-01-15",
        "texto_normal": "no es fecha"
    }
    contract = infer_contract_from_json(sample)

    for inp in contract.inputs:
        if inp.name == "fecha_creacion":
            assert inp.type == InputType.DATE
        elif inp.name == "texto_normal":
            assert inp.type == InputType.STR


def test_infer_contract_from_json_datetime_detection():
    """Test: strings con formato datetime se detectan como DATETIME."""
    sample = {
        "timestamp": "2024-01-15T10:30:00",
        "timestamp_z": "2024-01-15T10:30:00Z"
    }
    contract = infer_contract_from_json(sample)

    for inp in contract.inputs:
        assert inp.type == InputType.DATETIME
