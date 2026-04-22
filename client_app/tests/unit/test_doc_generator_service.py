"""
Tests para el servicio de generación de documentación.
TDD: Prompt 11 - Generador de README.md (documentación automática)

Secciones requeridas:
- # Título
- ## Propósito
- ## Requisitos de Entrada
- ## Resultados Esperados
- ## Guía de Ejecución
- ## Riesgos/Seguridad (AST)
- ## Changelog
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Importaciones que deben existir tras implementación
from client_app.app.services.doc_generator_service import (
    DocumentationGeneratorService,
    doc_generator
)


class TestDocumentationSections:
    """Tests para verificar que las secciones requeridas están presentes."""

    def test_readme_has_title_section(self):
        """README debe tener sección de título (#)."""
        script = MagicMock()
        script.name = "Mi Script de Prueba"
        script.id = 123
        script.status = "published"
        script.description = "Descripción de prueba"
        script.source_module = "custom"
        script.ui_contract = {"inputs": [], "outputs": []}
        script.data_contract = {}
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script)

        assert "# Mi Script de Prueba" in readme

    def test_readme_has_proposito_section(self):
        """README debe tener sección ## Propósito o ## Descripción."""
        script = MagicMock()
        script.name = "Test Script"
        script.id = 1
        script.status = "draft"
        script.description = "Este script hace X"
        script.source_module = "custom"
        script.ui_contract = {"inputs": [], "outputs": []}
        script.data_contract = {}
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script)

        # Debe tener Propósito o Descripción
        has_purpose = "## Propósito" in readme or "## Descripción" in readme
        assert has_purpose, f"README debe tener sección de propósito. Contenido: {readme[:500]}"

    def test_readme_has_inputs_section(self):
        """README debe documentar los requisitos de entrada."""
        script = MagicMock()
        script.name = "Test"
        script.id = 1
        script.status = "draft"
        script.description = "Test"
        script.source_module = "custom"
        script.ui_contract = {
            "inputs": [
                {"id": "file", "type": "file", "label": "Archivo Excel"}
            ],
            "outputs": []
        }
        script.data_contract = {}
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script)

        # Debe mencionar inputs o requisitos o contrato
        has_inputs = (
            "## Requisitos" in readme or
            "## Entrada" in readme or
            "Contrato" in readme or
            "inputs" in readme.lower()
        )
        assert has_inputs, f"README debe documentar entradas. Contenido: {readme}"


class TestDocumentationPersistence:
    """Tests para persistencia física de documentación."""

    def test_save_readme_to_disk(self):
        """Debe guardar README en data/automations/docs/[id].md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "automations" / "docs"

            script = MagicMock()
            script.name = "Test Script"
            script.id = 42
            script.status = "published"
            script.description = "Test"
            script.source_module = "custom"
            script.ui_contract = {"inputs": [], "outputs": []}
            script.data_contract = {}
            script.source_metadata = {}

            # Generar y guardar
            result_path = doc_generator.save_readme(
                script=script,
                base_path=docs_path
            )

            # Verificar que el archivo existe
            expected_path = docs_path / "42.md"
            assert result_path == expected_path
            assert expected_path.exists()

            # Verificar contenido
            content = expected_path.read_text(encoding='utf-8')
            assert "# Test Script" in content

    def test_save_creates_directory_if_not_exists(self):
        """Debe crear el directorio docs/ si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "new_folder" / "docs"

            script = MagicMock()
            script.name = "Test"
            script.id = 1
            script.status = "draft"
            script.description = ""
            script.source_module = "custom"
            script.ui_contract = {}
            script.data_contract = {}
            script.source_metadata = {}

            result_path = doc_generator.save_readme(script, docs_path)

            assert docs_path.exists()
            assert result_path.exists()


class TestZeroKnowledge:
    """Tests para garantizar Zero-Knowledge (sin PII ni datos reales)."""

    def test_readme_no_contains_pii_patterns(self):
        """README no debe contener patrones de PII."""
        script = MagicMock()
        script.name = "Extractor Facturas"
        script.id = 1
        script.status = "published"
        script.description = "Extrae datos de facturas"
        script.source_module = "extraction"
        script.ui_contract = {"inputs": [], "outputs": []}
        script.data_contract = {"output_schema": {"nif": "string", "email": "string"}}
        script.user_prompt = "Extrae NIF y email de facturas"
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script)

        # No debe contener ejemplos con datos reales tipo NIF o emails reales
        pii_patterns = [
            r'\d{8}[A-Z]',  # NIF español
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email real
        ]
        import re
        for pattern in pii_patterns:
            matches = re.findall(pattern, readme)
            # Permitir ejemplos sintéticos como "12345678A" o "ejemplo@test.com"
            for match in matches:
                assert match in ['12345678A', 'ejemplo@test.com', 'user@example.com'], \
                    f"README contiene posible PII: {match}"

    def test_readme_uses_synthetic_examples(self):
        """README debe usar ejemplos sintéticos, no datos reales."""
        script = MagicMock()
        script.name = "Test"
        script.id = 1
        script.status = "draft"
        script.description = "Procesa datos de clientes"
        script.source_module = "etl"
        script.ui_contract = {}
        script.data_contract = {
            "input_description": "CSV con nombres y emails",
            "output_description": "CSV limpio"
        }
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script)

        # No debe contener datos que parezcan reales
        assert "Juan Pérez" not in readme
        assert "maria.garcia@empresa.es" not in readme


class TestChangelogSection:
    """Tests para la sección de Changelog."""

    def test_readme_has_changelog_section(self):
        """README debe tener sección de Changelog."""
        script = MagicMock()
        script.name = "Test"
        script.id = 1
        script.status = "published"
        script.description = "Test"
        script.source_module = "custom"
        script.ui_contract = {}
        script.data_contract = {}
        script.source_metadata = {}
        script.created_at = None
        script.updated_at = None

        readme = doc_generator.generate_readme(script, include_changelog=True)

        assert "## Changelog" in readme or "## Historial" in readme


class TestSecuritySection:
    """Tests para la sección de Seguridad/Riesgos AST."""

    def test_readme_includes_security_warnings_for_risky_imports(self):
        """README debe advertir sobre imports potencialmente peligrosos."""
        script = MagicMock()
        script.name = "Script con OS"
        script.id = 1
        script.status = "draft"
        script.description = "Usa módulo os"
        script.source_module = "custom"
        script.ui_contract = {}
        script.data_contract = {}
        script.source_metadata = {}

        # Código con imports peligrosos
        code = """
import os
import subprocess

def run():
    os.system('ls')
"""

        readme = doc_generator.generate_readme_with_code_analysis(
            script=script,
            code=code
        )

        # Debe mencionar riesgos o seguridad
        has_security = (
            "## Seguridad" in readme or
            "## Riesgos" in readme or
            "os" in readme.lower() and "import" in readme.lower()
        )
        assert has_security, f"README debe advertir sobre imports peligrosos"


class TestIntegrationWithLifecycle:
    """Tests de integración con el ciclo de vida del script."""

    @pytest.mark.asyncio
    async def test_generate_on_promotion(self):
        """Documentación debe generarse al promover script a biblioteca."""
        # Este test verifica la integración, no la generación en sí
        with patch.object(doc_generator, 'save_readme') as mock_save:
            mock_save.return_value = Path("/fake/path/1.md")

            script = MagicMock()
            script.id = 1
            script.name = "Test"
            script.status = "validated"
            script.source_module = "custom"
            script.ui_contract = {}
            script.data_contract = {}
            script.source_metadata = {}
            script.description = ""

            # Simular promoción
            result = doc_generator.generate_and_save(script, Path("/fake/docs"))

            mock_save.assert_called_once()


class TestI18nSupport:
    """Tests para soporte de internacionalización."""

    def test_readme_supports_spanish(self):
        """README debe soportar español por defecto."""
        script = MagicMock()
        script.name = "Mi Script"
        script.id = 1
        script.status = "draft"
        script.description = "Descripción en español"
        script.source_module = "custom"
        script.ui_contract = {}
        script.data_contract = {}
        script.source_metadata = {}

        readme = doc_generator.generate_readme(script, language='es')

        # Verificar que usa términos en español
        spanish_terms = ['Descripción', 'Tipo', 'Estado', 'Fecha']
        has_spanish = any(term in readme for term in spanish_terms)
        assert has_spanish, "README debe estar en español"
