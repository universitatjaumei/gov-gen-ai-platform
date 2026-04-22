# client_app/tests/unit/test_preview_data_service.py
"""
Tests unitarios para PreviewDataService.

Verifica:
1. generate_mock_from_contract() genera filas con los tipos correctos
2. get_preview_from_atom() retorna sample_data si existe
3. get_preview_from_atom() genera mock si no hay sample_data
4. Caché retorna resultado sin re-ejecutar (segunda llamada con misma key)
5. Manejo de errores en get_preview_from_previous_step()
6. _normalize_output_to_preview() maneja DataFrame, lista, dict y primitivos
"""
import json
import pytest
import asyncio
import time
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import pandas as pd

from client_app.app.services.preview_data_service import (
    PreviewDataService,
    PreviewResult,
    _preview_cache,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def service():
    """Instancia limpia del servicio (caché vacía)."""
    svc = PreviewDataService()
    # Limpiar caché global antes de cada test
    _preview_cache.clear()
    return svc


@pytest.fixture
def sample_contract():
    """Contrato de salida de ejemplo."""
    return {
        "properties": {
            "nombre": {"type": "string"},
            "edad": {"type": "integer"},
            "precio": {"type": "number"},
            "fecha": {"type": "date"},
            "activo": {"type": "boolean"},
        }
    }


@pytest.fixture
def mock_atom():
    """Átomo de ejemplo simulado."""
    atom = MagicMock()
    atom.id = 42
    atom.name = "API de Prueba"
    atom.sample_data = None
    atom.output_contract = None
    return atom


# ============================================================================
# TESTS: generate_mock_from_contract
# ============================================================================

class TestGenerateMockFromContract:

    @pytest.mark.asyncio
    async def test_genera_filas_por_defecto(self, service, sample_contract):
        result = await service.generate_mock_from_contract(sample_contract, num_rows=3)

        assert result.success is True
        assert result.source_type == "mock_data"
        assert result.is_real_execution is False
        assert len(result.rows) == 3
        assert result.preview_rows == 3

    @pytest.mark.asyncio
    async def test_columnas_correctas(self, service, sample_contract):
        result = await service.generate_mock_from_contract(sample_contract, num_rows=1)

        assert set(result.columns) == {"nombre", "edad", "precio", "fecha", "activo"}

    @pytest.mark.asyncio
    async def test_tipos_generados_correctamente(self, service, sample_contract):
        result = await service.generate_mock_from_contract(sample_contract, num_rows=2)

        for row in result.rows:
            assert isinstance(row["nombre"], str)
            assert isinstance(row["edad"], int)
            assert isinstance(row["precio"], float)
            assert isinstance(row["fecha"], str)  # date como ISO string
            assert isinstance(row["activo"], bool)

    @pytest.mark.asyncio
    async def test_heuristica_email(self, service):
        contract = {"properties": {"email_usuario": {"type": "string"}}}
        result = await service.generate_mock_from_contract(contract, num_rows=2)

        for row in result.rows:
            assert "@" in row["email_usuario"]

    @pytest.mark.asyncio
    async def test_contrato_vacio(self, service):
        result = await service.generate_mock_from_contract({}, num_rows=3)

        # Sin propiedades: resultado vacío pero success=True
        assert result.success is True
        assert result.rows == []

    @pytest.mark.asyncio
    async def test_formato_alternativo_plano(self, service):
        """Soporta formato plano {campo: tipo} además de JSON Schema."""
        contract = {
            "id": "integer",
            "nombre": "string",
        }
        result = await service.generate_mock_from_contract(contract, num_rows=2)

        assert result.success is True
        assert len(result.rows) == 2
        assert "id" in result.columns
        assert "nombre" in result.columns


# ============================================================================
# TESTS: get_preview_from_atom
# ============================================================================

class TestGetPreviewFromAtom:

    @pytest.mark.asyncio
    async def test_retorna_sample_data_si_existe(self, service, mock_atom):
        sample = {
            "rows": [{"col": "val1"}, {"col": "val2"}],
            "columns": ["col"],
            "generated_at": "2025-01-01",
            "source": "manual"
        }
        mock_atom.sample_data = json.dumps(sample)

        with patch("client_app.app.services.preview_data_service.preview_data_service") as _:
            with patch(
                "client_app.app.services.atom_service.atom_service.get_atom",
                new=AsyncMock(return_value=mock_atom)
            ):
                with patch(
                    "client_app.app.services.preview_data_service.PreviewDataService._cache_get",
                    return_value=None
                ):
                    result = await service.get_preview_from_atom(42, max_rows=10)

        assert result.success is True
        assert result.source_type == "sample_data"
        assert len(result.rows) == 2
        assert result.columns == ["col"]
        assert result.metadata["generated_at"] == "2025-01-01"

    @pytest.mark.asyncio
    async def test_genera_mock_si_no_hay_sample_data(self, service, mock_atom):
        mock_atom.sample_data = None
        mock_atom.output_contract = json.dumps({
            "properties": {"nombre": {"type": "string"}}
        })

        with patch(
            "client_app.app.services.atom_service.atom_service.get_atom",
            new=AsyncMock(return_value=mock_atom)
        ):
            with patch.object(service, "_cache_get", return_value=None):
                with patch.object(service, "_cache_set"):
                    result = await service.get_preview_from_atom(42, max_rows=5)

        assert result.success is True
        assert result.source_type == "mock_data"
        assert len(result.rows) <= 5

    @pytest.mark.asyncio
    async def test_retorna_sin_datos_si_no_hay_contrato(self, service, mock_atom):
        mock_atom.sample_data = None
        mock_atom.output_contract = None

        with patch(
            "client_app.app.services.atom_service.atom_service.get_atom",
            new=AsyncMock(return_value=mock_atom)
        ):
            with patch.object(service, "_cache_get", return_value=None):
                with patch.object(service, "_cache_set"):
                    result = await service.get_preview_from_atom(42)

        assert result.success is True
        assert result.rows == []
        assert "note" in result.metadata

    @pytest.mark.asyncio
    async def test_retorna_error_si_atom_no_existe(self, service):
        with patch(
            "client_app.app.services.atom_service.atom_service.get_atom",
            new=AsyncMock(return_value=None)
        ):
            with patch.object(service, "_cache_get", return_value=None):
                result = await service.get_preview_from_atom(999)

        assert result.success is False
        assert "999" in result.error


# ============================================================================
# TESTS: Caché
# ============================================================================

class TestCache:

    def test_cache_miss_retorna_none(self, service):
        result = service._cache_get("key_inexistente")
        assert result is None

    def test_cache_hit_retorna_resultado(self, service):
        expected = PreviewResult(success=True, columns=["a"], rows=[{"a": 1}])
        service._cache_set("mi_key", expected)

        result = service._cache_get("mi_key")
        assert result is expected

    def test_cache_expira_con_ttl(self, service):
        """Simula expiración TTL manipulando el timestamp."""
        expected = PreviewResult(success=True)
        key = "expiring_key"
        
        # Guardar con timestamp muy antiguo
        _preview_cache[key] = (time.monotonic() - 99999, expected)
        
        result = service._cache_get(key)
        assert result is None  # Expiró
        assert key not in _preview_cache  # Se eliminó

    def test_invalidate_flow_cache_elimina_entradas(self, service):
        flow_id = 10
        service._cache_set(f"step:{flow_id}:0", PreviewResult(success=True))
        service._cache_set(f"step:{flow_id}:1", PreviewResult(success=True))
        service._cache_set("step:99:0", PreviewResult(success=True))  # Otro flujo

        service.invalidate_flow_cache(flow_id)

        assert service._cache_get(f"step:{flow_id}:0") is None
        assert service._cache_get(f"step:{flow_id}:1") is None
        # El otro flujo no se ve afectado
        assert service._cache_get("step:99:0") is not None


# ============================================================================
# TESTS: _normalize_output_to_preview
# ============================================================================

class TestNormalizeOutput:

    def test_dataframe_se_normaliza_correctamente(self, service):
        df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
        result = service._normalize_output_to_preview(df, "etl_transform", max_rows=10)

        assert result.success is True
        assert result.source_type == "executed_step"
        assert result.is_real_execution is True
        assert result.columns == ["col_a", "col_b"]
        assert result.row_count == 3
        assert len(result.rows) == 3

    def test_dataframe_trunca_filas(self, service):
        df = pd.DataFrame({"n": list(range(100))})
        result = service._normalize_output_to_preview(df, "etl_transform", max_rows=5)

        assert result.preview_rows == 5
        assert result.row_count == 100

    def test_lista_de_dicts_normaliza(self, service):
        items = [{"id": i, "name": f"item_{i}"} for i in range(20)]
        result = service._normalize_output_to_preview(items, "folder_scan", max_rows=10)

        assert result.success is True
        assert result.row_count == 20
        assert result.preview_rows == 10

    def test_lista_de_primitivos(self, service):
        items = ["archivo1.txt", "archivo2.pdf"]
        result = service._normalize_output_to_preview(items, "folder_scan", max_rows=10)

        assert result.success is True
        assert result.columns == ["value"]

    def test_dict_simple_como_clave_valor(self, service):
        output = {"nombre": "Ana", "edad": 30}
        result = service._normalize_output_to_preview(output, "extraction", max_rows=10)

        assert result.success is True
        assert "campo" in result.columns
        assert "valor" in result.columns

    def test_dict_con_lista_interna(self, service):
        output = {"items": [{"sku": "A1"}, {"sku": "A2"}], "total": 2}
        result = service._normalize_output_to_preview(output, "api_fetch", max_rows=10)

        assert result.success is True
        # Debe extraer la lista interna
        assert "sku" in result.columns

    def test_none_retorna_preview_vacio_exitoso(self, service):
        result = service._normalize_output_to_preview(None, "scheduler", max_rows=10)

        assert result.success is True
        assert result.rows == []

    def test_primitivo_en_fila(self, service):
        result = service._normalize_output_to_preview("texto de ejemplo", "llm_process", max_rows=10)

        assert result.success is True
        assert result.columns == ["resultado"]
        assert result.rows[0]["resultado"] == "texto de ejemplo"


# ============================================================================
# TESTS: get_preview_from_previous_step (error handling)
# ============================================================================

class TestGetPreviewFromPreviousStep:

    @pytest.mark.asyncio
    async def test_error_si_step_index_invalido(self, service):
        result = await service.get_preview_from_previous_step(
            flow_id=1,
            source_step_index=99,
            all_steps_config=[{"type": "api_fetch", "name": "API", "config": {}}]
        )
        assert result.success is False
        assert "99" in result.error or "no encontrado" in result.error.lower()

    @pytest.mark.asyncio
    async def test_timeout_genera_error_descriptivo(self, service):
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(999)

        with patch.object(service, "_execute_step_for_preview", side_effect=slow_execution):
            with patch.object(service, "_cache_get", return_value=None):
                result = await service.get_preview_from_previous_step(
                    flow_id=1,
                    source_step_index=0,
                    all_steps_config=[{"type": "api_fetch", "name": "Mi API", "config": {}}],
                    timeout_seconds=0.1
                )

        assert result.success is False
        assert "agotado" in result.error.lower() or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_retorna_cache_si_existe(self, service):
        cached_result = PreviewResult(success=True, columns=["x"], rows=[{"x": 1}], source_type="executed_step")
        service._cache_set("step:5:2", cached_result)

        # El método _execute_step_for_preview NO debe ser llamado
        with patch.object(service, "_execute_step_for_preview") as mock_exec:
            result = await service.get_preview_from_previous_step(
                flow_id=5,
                source_step_index=2,
                all_steps_config=[
                    {"type": "api_fetch", "name": "API", "config": {}},
                    {"type": "api_fetch", "name": "API2", "config": {}},
                    {"type": "etl_transform", "name": "ETL", "config": {}},
                ]
            )
            mock_exec.assert_not_called()

        assert result is cached_result
