# client_app/tests/ui/test_copilot_drawer.py
"""
Test TDD for TabbedSideDrawer and Copilot UI Component.
Prompt #8: Arquitectura de "Side-Tabs" para el Drawer y Componente Copiloto.

Tests the tabbed drawer structure with Settings, Variables, and Copilot tabs.
"""
import pytest
from typing import Dict, Any, List, Optional

from client_app.app.ui.components.side_drawer import TabbedSideDrawer, TabConfig


class TestTabbedSideDrawerInitialization:
    """Tests for TabbedSideDrawer initialization."""

    def test_drawer_tabs_initialization(self):
        """Test that drawer initializes with required tabs."""
        drawer = TabbedSideDrawer(title="Configuración")

        # Validate that the 3 required tabs exist
        assert "settings" in drawer.tabs
        assert "variables" in drawer.tabs
        assert "copilot" in drawer.tabs

    def test_drawer_default_tab_is_settings(self):
        """Test that default tab is settings."""
        drawer = TabbedSideDrawer(title="Test")
        assert drawer.current_tab == "settings"

    def test_drawer_tab_icons(self):
        """Test that tabs have correct icons."""
        drawer = TabbedSideDrawer(title="Test")

        assert drawer.tabs["settings"].icon == "settings"
        assert drawer.tabs["variables"].icon == "account_tree"
        assert drawer.tabs["copilot"].icon == "auto_awesome"

    def test_drawer_tab_labels(self):
        """Test that tabs have correct labels."""
        drawer = TabbedSideDrawer(title="Test")

        assert drawer.tabs["settings"].label == "Ajustes"
        assert drawer.tabs["variables"].label == "Variables"
        assert drawer.tabs["copilot"].label == "Copiloto"


class TestCopilotNotificationLogic:
    """Tests for copilot notification system."""

    def test_initial_no_notification(self):
        """Test that copilot starts without notification."""
        drawer = TabbedSideDrawer(title="Test")
        assert drawer.copilot_has_notification is False

    def test_notify_suggestion_available(self):
        """Test that notification can be activated."""
        drawer = TabbedSideDrawer(title="Test")

        # Activate notification
        drawer.notify_suggestion_available()

        # Verify state changed
        assert drawer.copilot_has_notification is True

    def test_clear_notification(self):
        """Test that notification can be cleared."""
        drawer = TabbedSideDrawer(title="Test")

        # Activate then clear
        drawer.notify_suggestion_available()
        drawer.clear_copilot_notification()

        assert drawer.copilot_has_notification is False

    def test_switching_to_copilot_clears_notification(self):
        """Test that switching to copilot tab clears notification."""
        drawer = TabbedSideDrawer(title="Test")

        drawer.notify_suggestion_available()
        drawer.switch_to("copilot")

        # Notification should be cleared when user views copilot
        assert drawer.copilot_has_notification is False


class TestTabSwitching:
    """Tests for tab switching functionality."""

    def test_switch_to_valid_tab(self):
        """Test switching to a valid tab."""
        drawer = TabbedSideDrawer(title="Test")

        drawer.switch_to("copilot")
        assert drawer.current_tab == "copilot"

        drawer.switch_to("variables")
        assert drawer.current_tab == "variables"

        drawer.switch_to("settings")
        assert drawer.current_tab == "settings"

    def test_switch_to_invalid_tab_ignored(self):
        """Test that switching to invalid tab is ignored."""
        drawer = TabbedSideDrawer(title="Test")
        original_tab = drawer.current_tab

        drawer.switch_to("nonexistent_tab")

        # Should remain on original tab
        assert drawer.current_tab == original_tab

    def test_tab_change_callback(self):
        """Test that tab change triggers callback."""
        drawer = TabbedSideDrawer(title="Test")
        callback_called = {"value": False, "tab": None}

        def on_tab_change(tab_name: str):
            callback_called["value"] = True
            callback_called["tab"] = tab_name

        drawer.on_tab_change(on_tab_change)
        drawer.switch_to("variables")

        assert callback_called["value"] is True
        assert callback_called["tab"] == "variables"


class TestVariablesTabDataPills:
    """Tests for the Variables tab data pills functionality."""

    def test_set_contract_data(self):
        """Test setting contract data for variables display."""
        drawer = TabbedSideDrawer(title="Test")

        contract = {
            "inputs": [
                {"name": "input_file", "type": "FILE", "label": "Archivo"},
            ],
            "outputs": [
                {"name": "total", "type": "FLOAT", "label": "Total"},
            ]
        }

        drawer.set_contract(contract)

        assert drawer.contract is not None
        assert len(drawer.contract["inputs"]) == 1
        assert len(drawer.contract["outputs"]) == 1

    def test_detect_file_inputs(self):
        """Test detection of FILE type inputs."""
        drawer = TabbedSideDrawer(title="Test")

        contract = {
            "inputs": [
                {"name": "doc", "type": "FILE"},
                {"name": "text", "type": "STR"},
                {"name": "files", "type": "FILES"},
            ],
            "outputs": []
        }

        drawer.set_contract(contract)
        file_inputs = drawer.get_file_inputs()

        assert len(file_inputs) == 2
        assert file_inputs[0]["name"] == "doc"
        assert file_inputs[1]["name"] == "files"

    def test_no_file_inputs(self):
        """Test when no FILE inputs exist."""
        drawer = TabbedSideDrawer(title="Test")

        contract = {
            "inputs": [
                {"name": "name", "type": "STR"},
                {"name": "count", "type": "INT"},
            ],
            "outputs": []
        }

        drawer.set_contract(contract)
        file_inputs = drawer.get_file_inputs()

        assert len(file_inputs) == 0


class TestCopilotConfiguration:
    """Tests for copilot configuration and placeholder."""

    def test_copilot_placeholder_text(self):
        """Test that copilot has correct placeholder text."""
        drawer = TabbedSideDrawer(title="Test")

        expected_placeholder = "Pregunta sobre este átomo o cómo conectar variables..."
        assert drawer.copilot_placeholder == expected_placeholder

    def test_copilot_suggestions_list(self):
        """Test managing copilot suggestions."""
        drawer = TabbedSideDrawer(title="Test")

        # Initially empty
        assert len(drawer.copilot_suggestions) == 0

        # Add suggestion
        drawer.add_copilot_suggestion(
            message="Falta conexión entre 'total' y 'entrada'",
            severity="warning"
        )

        assert len(drawer.copilot_suggestions) == 1
        assert drawer.copilot_suggestions[0]["severity"] == "warning"

    def test_adding_suggestion_triggers_notification(self):
        """Test that adding suggestion triggers notification."""
        drawer = TabbedSideDrawer(title="Test")

        drawer.add_copilot_suggestion(
            message="Sugerencia de conexión",
            severity="info"
        )

        assert drawer.copilot_has_notification is True


class TestStatePersistence:
    """Tests for drawer state persistence."""

    def test_get_state(self):
        """Test getting drawer state."""
        drawer = TabbedSideDrawer(title="Test")
        drawer.switch_to("variables")
        drawer.notify_suggestion_available()

        state = drawer.get_state()

        assert state["current_tab"] == "variables"
        assert state["copilot_has_notification"] is True

    def test_restore_state(self):
        """Test restoring drawer state."""
        drawer = TabbedSideDrawer(title="Test")

        saved_state = {
            "current_tab": "copilot",
            "copilot_has_notification": True
        }

        drawer.restore_state(saved_state)

        assert drawer.current_tab == "copilot"
        # Note: restoring copilot tab clears notification
        # so has_notification should be False after restore if tab is copilot


class TestTabConfig:
    """Tests for TabConfig dataclass."""

    def test_tab_config_creation(self):
        """Test creating a TabConfig."""
        config = TabConfig(
            name="test",
            label="Test Tab",
            icon="settings",
            tooltip="A test tab"
        )

        assert config.name == "test"
        assert config.label == "Test Tab"
        assert config.icon == "settings"
        assert config.tooltip == "A test tab"

    def test_tab_config_defaults(self):
        """Test TabConfig default values."""
        config = TabConfig(
            name="test",
            label="Test",
            icon="help"
        )

        assert config.tooltip is None


class TestCSSStyles:
    """Tests for CSS style generation."""

    def test_pulse_animation_css(self):
        """Test that pulse animation CSS is generated."""
        drawer = TabbedSideDrawer(title="Test")
        css = drawer.get_copilot_pulse_css()

        assert "@keyframes" in css
        assert "copilot-pulse" in css
        assert "#FFB300" in css or "amber" in css.lower()

    def test_tab_styles_css(self):
        """Test that tab styles CSS is generated."""
        drawer = TabbedSideDrawer(title="Test")
        css = drawer.get_tab_styles_css()

        assert "vertical" in css.lower() or "tabs" in css.lower()
