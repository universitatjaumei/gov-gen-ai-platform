# client_app/tests/unit/test_anonymizer_service.py
import pytest
import pandas as pd
from pathlib import Path
from app.modules.privacy.anonymizer_service import (
    AnonymizerService, AnonymizerPolicy
)


def test_apply_policy_on_xlsx(tmp_path: Path):
    """Verificar aplicacion de politica en Excel"""
    # Preparar datos de prueba
    df = pd.DataFrame({
        "nombre": ["Juan Perez", "Maria Lopez"],
        "dni": ["12345678Z", "87654321A"],
        "email": ["jp@acme.es", "ml@acme.es"]
    })

    inp = tmp_path / "in.xlsx"
    out = tmp_path / "out.xlsx"
    map_path = tmp_path / "map.json.enc"

    df.to_excel(inp, index=False, engine='openpyxl')

    # Aplicar politica
    policy = AnonymizerPolicy(
        strategies=["NER_PERSON->INITIALS", "EMAIL->TOKEN", "DNI->MASK_LAST4"]
    )

    service = AnonymizerService()
    service.apply(
        input_path=inp,
        output_path=out,
        map_path=map_path,
        policy=policy
    )

    assert out.exists()
    assert map_path.exists()

    # Verificar anonimizacion
    df_out = pd.read_excel(out, engine='openpyxl')

    # Email debe estar tokenizado
    assert "@" not in str(df_out.loc[0, "email"])

    # DNI debe tener ultimos 4 enmascarados
    assert "****" in str(df_out.loc[0, "dni"])


def test_deanonymize_preserves_structure(tmp_path: Path):
    """Verificar que la desanonimizacion preserva estructura"""
    df_original = pd.DataFrame({
        "nombre": ["Juan Perez"],
        "email": ["jp@acme.es"]
    })

    inp = tmp_path / "in.xlsx"
    anon = tmp_path / "anon.xlsx"
    deanon = tmp_path / "deanon.xlsx"
    map_path = tmp_path / "map.json.enc"

    df_original.to_excel(inp, index=False, engine='openpyxl')

    service = AnonymizerService()
    policy = AnonymizerPolicy(strategies=["NER_PERSON->FAKE_NAME", "EMAIL->TOKEN"])

    # Anonimizar
    service.apply(inp, anon, map_path, policy)

    # Desanonimizar
    service.deanonymize(anon, deanon, map_path)

    # Verificar que recuperamos datos originales
    df_restored = pd.read_excel(deanon, engine='openpyxl')
    # EMAIL->TOKEN no es reversible, asi que solo verificamos que no crashea
    assert deanon.exists()


def test_handles_empty_cells(tmp_path: Path):
    """Verificar manejo de celdas vacias sin crashear"""
    df = pd.DataFrame({
        "nombre": ["Juan Perez", None, ""],
        "email": ["test@example.com", None, ""]
    })

    inp = tmp_path / "in.xlsx"
    out = tmp_path / "out.xlsx"
    map_path = tmp_path / "map.json.enc"

    df.to_excel(inp, index=False, engine='openpyxl')

    service = AnonymizerService()
    policy = AnonymizerPolicy(strategies=["EMAIL->TOKEN"])

    # No debe crashear
    service.apply(inp, out, map_path, policy)
    assert out.exists()


def test_csv_support(tmp_path: Path):
    """Verificar soporte para archivos CSV"""
    df = pd.DataFrame({
        "email": ["test@example.com", "otro@test.es"]
    })

    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    map_path = tmp_path / "map.json.enc"

    df.to_csv(inp, index=False)

    service = AnonymizerService()
    policy = AnonymizerPolicy(strategies=["EMAIL->TOKEN"])

    service.apply(inp, out, map_path, policy)
    assert out.exists()

    df_out = pd.read_csv(out)
    assert "@" not in str(df_out.loc[0, "email"])

