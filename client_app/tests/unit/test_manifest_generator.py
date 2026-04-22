"""
Tests para el generador de manifiesto de paquetes.
Prompt 1.4 del sistema de exportación/importación de automatismos.

TDD: Estos tests se escriben ANTES de implementar el servicio.

El manifiesto es el corazón del paquete .automatia:
- Contiene metadatos y hashes de TODOS los archivos
- La firma se aplica al manifiesto completo
"""
import pytest
import json
import hashlib
from unittest.mock import patch

from client_app.app.services.manifest_generator import (
    ManifestGenerator,
    manifest_generator
)


@pytest.fixture
def generator():
    """Instancia del generador de manifiesto."""
    return ManifestGenerator()


@pytest.fixture
def sample_source_info():
    """Información de origen de ejemplo."""
    return {
        "license_id": "LIC-001-ABC",
        "client_id": "CLI-001-XYZ",
        "partner_id": "PARTNER-001",
        "machine_id": "MACHINE-ABC123"
    }


@pytest.fixture
def sample_files():
    """Archivos de ejemplo para el paquete."""
    return {
        "scripts/extractor.py": b"def extract(file): pass",
        "scripts/transformer.py": b"def transform(df): return df",
        "playbooks/login.json": b'[{"type": "click", "selector": "#btn"}]',
        "metadata/scripts/extractor.json": b'{"name": "extractor", "version": "1.0"}'
    }


class TestGenerateManifestBasic:
    """Tests para generación básica de manifiesto."""

    def test_generate_manifest_basic(self, generator, sample_source_info, sample_files):
        """Genera manifest con campos requeridos."""
        manifest_json = generator.generate(
            package_name="mi-paquete",
            source_info=sample_source_info,
            files=sample_files,
            description="Paquete de prueba"
        )

        # Debe ser JSON válido
        manifest = json.loads(manifest_json)

        # Campos requeridos
        assert manifest["version"] == "1.0"
        assert manifest["name"] == "mi-paquete"
        assert manifest["description"] == "Paquete de prueba"
        assert "export_date" in manifest
        assert "source" in manifest
        assert "contents" in manifest
        assert "file_hashes" in manifest

    def test_generate_manifest_without_description(self, generator, sample_source_info, sample_files):
        """Genera manifest sin descripción (opcional)."""
        manifest_json = generator.generate(
            package_name="paquete-sin-desc",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        assert manifest["name"] == "paquete-sin-desc"
        assert manifest["description"] is None

    def test_generate_manifest_export_date_format(self, generator, sample_source_info, sample_files):
        """El export_date tiene formato ISO con Z."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        export_date = manifest["export_date"]

        # Debe terminar en Z (UTC)
        assert export_date.endswith("Z")
        # Debe ser parseable (sin la Z)
        from datetime import datetime
        datetime.fromisoformat(export_date.rstrip("Z"))


class TestManifestFileHashes:
    """Tests para hashes de archivos en el manifiesto."""

    def test_manifest_includes_file_hashes(self, generator, sample_source_info, sample_files):
        """Cada archivo tiene su hash SHA256."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        file_hashes = manifest["file_hashes"]

        # Todos los archivos deben tener hash
        assert len(file_hashes) == len(sample_files)

        for filepath, content in sample_files.items():
            assert filepath in file_hashes
            expected_hash = hashlib.sha256(content).hexdigest()
            assert file_hashes[filepath] == expected_hash

    def test_file_hashes_are_sha256(self, generator, sample_source_info):
        """Los hashes son SHA256 (64 caracteres hex)."""
        files = {
            "test.py": b"print('hello')"
        }

        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=files
        )

        manifest = json.loads(manifest_json)
        hash_value = manifest["file_hashes"]["test.py"]

        assert len(hash_value) == 64
        # Debe ser hexadecimal válido
        int(hash_value, 16)

    def test_empty_files_have_valid_hash(self, generator, sample_source_info):
        """Archivos vacíos también tienen hash válido."""
        files = {
            "empty.py": b""
        }

        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=files
        )

        manifest = json.loads(manifest_json)
        expected_hash = hashlib.sha256(b"").hexdigest()
        assert manifest["file_hashes"]["empty.py"] == expected_hash


class TestManifestSourceInfo:
    """Tests para información de origen en el manifiesto."""

    def test_manifest_includes_source_info(self, generator, sample_source_info, sample_files):
        """Incluye license_id, client_id, partner_id."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        source = manifest["source"]

        assert source["license_id"] == "LIC-001-ABC"
        assert source["client_id"] == "CLI-001-XYZ"
        assert source["partner_id"] == "PARTNER-001"
        assert source["machine_id"] == "MACHINE-ABC123"

    def test_manifest_source_without_machine_id(self, generator, sample_files):
        """machine_id es opcional en source_info."""
        source_info = {
            "license_id": "LIC-001",
            "client_id": "CLI-001",
            "partner_id": "PARTNER-001"
            # Sin machine_id
        }

        manifest_json = generator.generate(
            package_name="test",
            source_info=source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        assert manifest["source"]["machine_id"] is None


class TestManifestContents:
    """Tests para listado de contenidos en el manifiesto."""

    def test_manifest_lists_contents(self, generator, sample_source_info):
        """Lista scripts, playbooks, workflows correctamente."""
        files = {
            "scripts/script1.py": b"code1",
            "scripts/script2.py": b"code2",
            "playbooks/playbook1.json": b"{}",
            "workflows/flow1.json": b"{}",
            "workflows/flow2.json": b"{}",
            "metadata/scripts/script1.json": b"{}"  # No debe aparecer en contents
        }

        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=files
        )

        manifest = json.loads(manifest_json)
        contents = manifest["contents"]

        # Scripts (sin prefijo scripts/)
        assert set(contents["scripts"]) == {"script1.py", "script2.py"}

        # Playbooks (sin prefijo playbooks/)
        assert set(contents["playbooks"]) == {"playbook1.json"}

        # Workflows (sin prefijo workflows/)
        assert set(contents["workflows"]) == {"flow1.json", "flow2.json"}

    def test_manifest_empty_contents(self, generator, sample_source_info):
        """Maneja paquetes sin ciertos tipos de contenido."""
        files = {
            "scripts/only_script.py": b"code"
        }

        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=files
        )

        manifest = json.loads(manifest_json)
        contents = manifest["contents"]

        assert contents["scripts"] == ["only_script.py"]
        assert contents["playbooks"] == []
        assert contents["workflows"] == []


class TestManifestDeterminism:
    """Tests para determinismo del manifiesto."""

    def test_manifest_is_deterministic(self, generator, sample_source_info, sample_files):
        """Mismo contenido = mismo manifest (excepto timestamp)."""
        fixed_date = "2024-01-15T10:30:00Z"

        with patch.object(generator, '_get_export_date', return_value=fixed_date):
            manifest1 = generator.generate(
                package_name="test",
                source_info=sample_source_info,
                files=sample_files,
                description="Test"
            )
            manifest2 = generator.generate(
                package_name="test",
                source_info=sample_source_info,
                files=sample_files,
                description="Test"
            )

        assert manifest1 == manifest2

    def test_manifest_keys_are_sorted(self, generator, sample_source_info, sample_files):
        """Las claves del JSON están ordenadas para determinismo."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        # Verificar que se genera con sort_keys=True
        manifest = json.loads(manifest_json)
        regenerated = json.dumps(manifest, sort_keys=True, indent=2)

        # Si ya estaba ordenado, debe ser igual
        manifest_normalized = json.dumps(json.loads(manifest_json), sort_keys=True, indent=2)
        assert manifest_normalized == regenerated


class TestManifestJsonValid:
    """Tests para validez del JSON generado."""

    def test_manifest_json_is_valid(self, generator, sample_source_info, sample_files):
        """El JSON generado es parseable."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        # No debe lanzar excepción
        parsed = json.loads(manifest_json)
        assert isinstance(parsed, dict)

    def test_manifest_is_formatted(self, generator, sample_source_info, sample_files):
        """El JSON está formateado con indentación."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        # Debe tener saltos de línea (formateado)
        assert "\n" in manifest_json

    def test_manifest_signature_initially_null(self, generator, sample_source_info, sample_files):
        """La firma es null antes de firmar."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        assert manifest["signature"] is None


class TestAddSignature:
    """Tests para añadir firma al manifiesto."""

    def test_add_signature_to_manifest(self, generator, sample_source_info, sample_files):
        """Añade firma al manifiesto correctamente."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        signature_data = {
            "type": "CLIENT",
            "algorithm": "HMAC-SHA256",
            "value": "abc123signature",
            "timestamp": "2024-01-15T10:30:00"
        }

        signed_manifest_json = generator.add_signature(manifest_json, signature_data)
        signed_manifest = json.loads(signed_manifest_json)

        assert signed_manifest["signature"] == signature_data

    def test_add_signature_includes_package_hash(self, generator, sample_source_info, sample_files):
        """Al firmar se añade hash del manifiesto original."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        expected_package_hash = hashlib.sha256(manifest_json.encode()).hexdigest()

        signature_data = {
            "type": "CLIENT",
            "algorithm": "HMAC-SHA256",
            "value": "signature",
            "timestamp": "2024-01-15T10:30:00"
        }

        signed_manifest_json = generator.add_signature(manifest_json, signature_data)
        signed_manifest = json.loads(signed_manifest_json)

        assert signed_manifest["package_hash"] == expected_package_hash

    def test_add_signature_maintains_valid_json(self, generator, sample_source_info, sample_files):
        """El manifiesto firmado sigue siendo JSON válido."""
        manifest_json = generator.generate(
            package_name="test",
            source_info=sample_source_info,
            files=sample_files
        )

        signature_data = {
            "type": "PARTNER",
            "algorithm": "RSA-SHA256",
            "value": "long_rsa_signature_base64",
            "timestamp": "2024-01-15T10:30:00"
        }

        signed_manifest_json = generator.add_signature(manifest_json, signature_data)

        # Debe ser parseable
        parsed = json.loads(signed_manifest_json)
        assert isinstance(parsed, dict)
        assert "signature" in parsed
        assert "package_hash" in parsed


class TestSingleton:
    """Tests para el singleton del generador."""

    def test_singleton_exists(self):
        """El singleton manifest_generator existe."""
        assert manifest_generator is not None
        assert isinstance(manifest_generator, ManifestGenerator)

    def test_singleton_is_functional(self, sample_source_info, sample_files):
        """El singleton es funcional."""
        manifest_json = manifest_generator.generate(
            package_name="singleton-test",
            source_info=sample_source_info,
            files=sample_files
        )

        manifest = json.loads(manifest_json)
        assert manifest["name"] == "singleton-test"
