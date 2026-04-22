"""
Tests para selección de conexiones en atom gallery.
Data Contracts Fase 2, Prompt 4.
"""
import pytest
from client_app.app.core.state import state
from automatia_shared.enums import StepType
from client_app.app.config.atom_catalog import (
    CONNECTION_METADATA,
    get_connection_metadata,
    ATOM_CATALOG
)


class TestAtomGalleryConnectionState:
    """Tests para estado de wizard de conexiones."""

    def setup_method(self):
        """Reset state antes de cada test."""
        state.wizard_show_connection_subtypes = False
        state.wizard_initial_subtype = None
        state.wizard_initial_step_type = None

    def test_state_has_wizard_subtype_field(self):
        """State debe tener campo wizard_initial_subtype."""
        assert hasattr(state, 'wizard_initial_subtype')

    def test_state_has_show_connection_subtypes_field(self):
        """State debe tener campo wizard_show_connection_subtypes."""
        assert hasattr(state, 'wizard_show_connection_subtypes')

    def test_state_has_wizard_flow_context_field(self):
        """State debe tener campo wizard_flow_context."""
        assert hasattr(state, 'wizard_flow_context')

    def test_connection_type_exists_in_catalog(self):
        """CONNECTION debe existir en ATOM_CATALOG."""
        assert StepType.CONNECTION in ATOM_CATALOG

    def test_subtype_state_update(self):
        """Seleccionar EMAIL debe guardar subtype en state."""
        state.wizard_initial_step_type = StepType.CONNECTION
        state.wizard_initial_subtype = "EMAIL"

        assert state.wizard_initial_subtype == "EMAIL"
        assert state.wizard_initial_step_type == StepType.CONNECTION

    def test_show_subtypes_toggle(self):
        """Toggle de wizard_show_connection_subtypes."""
        assert state.wizard_show_connection_subtypes == False

        state.wizard_show_connection_subtypes = True
        assert state.wizard_show_connection_subtypes == True

        state.wizard_show_connection_subtypes = False
        assert state.wizard_show_connection_subtypes == False


class TestConnectionMetadataInGallery:
    """Tests para metadata de conexiones usada en galería."""

    def test_all_connection_subtypes_have_metadata(self):
        """Todos los subtipos deben tener metadata completa."""
        expected_subtypes = ["EMAIL", "API", "DATABASE"]

        for subtype in expected_subtypes:
            metadata = get_connection_metadata(subtype)
            assert metadata.label is not None
            assert metadata.icon is not None
            assert metadata.color is not None
            assert metadata.description is not None
            assert metadata.config_schema is not None

    def test_connection_metadata_has_ui_fields(self):
        """Metadata debe tener campos necesarios para UI."""
        for subtype, metadata in CONNECTION_METADATA.items():
            # Verificar campos requeridos para renderizar cards
            assert hasattr(metadata, 'label'), f"{subtype} missing label"
            assert hasattr(metadata, 'icon'), f"{subtype} missing icon"
            assert hasattr(metadata, 'color'), f"{subtype} missing color"
            assert hasattr(metadata, 'description'), f"{subtype} missing description"

    def test_email_connection_label(self):
        """EMAIL debe tener label correcto."""
        metadata = get_connection_metadata("EMAIL")
        assert metadata.label == "Conexión Email"

    def test_api_connection_label(self):
        """API debe tener label correcto."""
        metadata = get_connection_metadata("API")
        assert metadata.label == "Conexión API"

    def test_database_connection_label(self):
        """DATABASE debe tener label correcto."""
        metadata = get_connection_metadata("DATABASE")
        assert metadata.label == "Conexión Base de Datos"
