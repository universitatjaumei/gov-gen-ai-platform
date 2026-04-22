"""
Tests para metadata de conexiones en el catálogo.
TDD: Estos tests verifican el soporte de conexiones en atom_catalog.
Data Contracts Fase 1, Prompt 2.
"""
import pytest
from client_app.app.config.atom_catalog import (
    get_atom_metadata,
    get_connection_metadata,
    ATOM_CATALOG,
    CONNECTION_METADATA
)
from automatia_shared.enums import StepType


class TestConnectionCatalog:
    """Tests para verificar metadata de conexiones."""

    def test_connection_type_has_metadata(self):
        """
        StepType.CONNECTION debe tener metadata en el catálogo.
        """
        metadata = get_atom_metadata(StepType.CONNECTION)
        assert metadata is not None
        assert metadata.label is not None
        assert metadata.icon is not None

    def test_email_connection_subtype_metadata(self):
        """
        Subtipo EMAIL debe tener metadata específica.
        """
        metadata = get_connection_metadata("EMAIL")
        assert metadata.label == "Conexión Email"
        assert metadata.icon == "email"
        assert metadata.color == "blue"

    def test_api_connection_subtype_metadata(self):
        """
        Subtipo API debe tener metadata específica.
        """
        metadata = get_connection_metadata("API")
        assert metadata.label == "Conexión API"
        assert metadata.icon == "api"
        assert metadata.color == "green"

    def test_database_connection_subtype_metadata(self):
        """
        Subtipo DATABASE debe tener metadata específica.
        """
        metadata = get_connection_metadata("DATABASE")
        assert metadata.label == "Conexión Base de Datos"
        assert metadata.icon == "storage"
        assert metadata.color == "purple"

    def test_ftp_connection_subtype_metadata(self):
        """
        Subtipo FTP debe tener metadata específica.
        """
        metadata = get_connection_metadata("FTP")
        assert metadata.label == "Conexión FTP/SFTP"
        assert metadata.icon == "folder_shared"
        assert metadata.color == "orange"

    def test_email_connection_has_config_schema(self):
        """
        Conexión EMAIL debe tener schema de configuración predefinido.
        """
        metadata = get_connection_metadata("EMAIL")
        schema = metadata.config_schema

        assert schema is not None
        assert "host" in schema["properties"]
        assert "port" in schema["properties"]
        assert "username" in schema["properties"]
        assert "password" in schema["properties"]
        assert schema["properties"]["password"]["format"] == "password"

    def test_api_connection_has_config_schema(self):
        """
        Conexión API debe tener schema de configuración predefinido.
        """
        metadata = get_connection_metadata("API")
        schema = metadata.config_schema

        assert schema is not None
        assert "base_url" in schema["properties"]
        assert "api_key" in schema["properties"]
        assert "headers" in schema["properties"]

    def test_database_connection_has_config_schema(self):
        """
        Conexión DATABASE debe tener schema de configuración.
        """
        metadata = get_connection_metadata("DATABASE")
        schema = metadata.config_schema

        assert schema is not None
        assert "db_type" in schema["properties"]
        assert "host" in schema["properties"]
        assert "database" in schema["properties"]

    def test_ftp_connection_has_config_schema(self):
        """
        Conexión FTP debe tener schema de configuración.
        """
        metadata = get_connection_metadata("FTP")
        schema = metadata.config_schema

        assert schema is not None
        assert "host" in schema["properties"]
        assert "username" in schema["properties"]
        assert "use_sftp" in schema["properties"]


class TestConnectionCatalogIntegration:
    """Tests de integración del catálogo de conexiones."""

    def test_all_connection_subtypes_exist(self):
        """Verificar que todos los subtipos esperados existen."""
        expected_subtypes = ["EMAIL", "API", "DATABASE", "FTP"]
        for subtype in expected_subtypes:
            assert subtype in CONNECTION_METADATA, f"Subtipo {subtype} no existe"

    def test_connection_in_atom_catalog(self):
        """CONNECTION debe estar en el catálogo principal."""
        assert StepType.CONNECTION in ATOM_CATALOG

    def test_get_connection_metadata_invalid_subtype(self):
        """Debe lanzar KeyError para subtipos inválidos."""
        with pytest.raises(KeyError):
            get_connection_metadata("INVALID_SUBTYPE")
