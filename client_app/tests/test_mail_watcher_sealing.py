# client_app/tests/test_mail_watcher_sealing.py
"""
Test TDD for MailWatcher Sealing (Contract Inheritance).
Prompt #6: El "Sello" para MailWatchers.

Tests that MailWatchers inherit contracts from their linked extraction templates
and combine them with email-specific fields.
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from automatia_shared.contracts.ui_contract import InputType


class TestMailWatcherContractInheritance:
    """Tests for MailWatcher contract inheritance from extraction templates."""

    def test_mail_watcher_inherits_template_contract(self):
        """
        Test that a MailWatcher's contract includes fields from
        its linked extraction template.
        """
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        # 1. Setup: Template contract with extraction fields
        template_contract = {
            "inputs": [],
            "outputs": [
                {"name": "total_factura", "type": "int", "label": "Total Factura"},
                {"name": "cif_emisor", "type": "str", "label": "CIF Emisor"}
            ]
        }

        # 2. Build MailWatcher contract
        watcher_contract = build_mail_watcher_contract(
            name="Watcher Facturas",
            template_contract=template_contract,
            email_account="facturas@empresa.com",
            folder="INBOX"
        )

        # 3. Validate structure
        assert "inputs" in watcher_contract
        assert "outputs" in watcher_contract

        output_names = [o["name"] for o in watcher_contract["outputs"]]

        # Email fields should be present
        assert "email_sender" in output_names
        assert "email_subject" in output_names
        assert "email_date" in output_names
        assert "attachments" in output_names

        # Template fields should be inherited
        assert "total_factura" in output_names
        assert "cif_emisor" in output_names

    def test_mail_watcher_has_file_input(self):
        """Test that MailWatcher has attachments as FILES type."""
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        watcher_contract = build_mail_watcher_contract(
            name="Test Watcher",
            template_contract={"inputs": [], "outputs": []},
            email_account="test@test.com"
        )

        # Find attachments output
        attachments_output = next(
            (o for o in watcher_contract["outputs"] if o["name"] == "attachments"),
            None
        )

        assert attachments_output is not None
        assert attachments_output["type"] == InputType.FILES.value

    def test_mail_watcher_email_fields_types(self):
        """Test that email fields have correct types."""
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        watcher_contract = build_mail_watcher_contract(
            name="Test Watcher",
            template_contract={"inputs": [], "outputs": []},
            email_account="test@test.com"
        )

        outputs_by_name = {o["name"]: o for o in watcher_contract["outputs"]}

        # Verify types
        assert outputs_by_name["email_sender"]["type"] == InputType.STR.value
        assert outputs_by_name["email_subject"]["type"] == InputType.STR.value
        assert outputs_by_name["email_date"]["type"] == InputType.DATETIME.value
        assert outputs_by_name["email_body"]["type"] == InputType.STR.value

    def test_mail_watcher_without_template(self):
        """Test MailWatcher contract when no template is linked."""
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        watcher_contract = build_mail_watcher_contract(
            name="Simple Email Watcher",
            template_contract=None,  # No template
            email_account="alerts@empresa.com"
        )

        output_names = [o["name"] for o in watcher_contract["outputs"]]

        # Should still have email fields
        assert "email_sender" in output_names
        assert "email_subject" in output_names
        assert "attachments" in output_names

        # Should have exactly the base email fields (no extraction fields)
        assert len(watcher_contract["outputs"]) == 5  # sender, subject, date, body, attachments

    def test_inherited_fields_marked_optional(self):
        """Test that inherited extraction fields are marked as optional."""
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        template_contract = {
            "inputs": [],
            "outputs": [
                {"name": "campo_extraido", "type": "str", "required": True}
            ]
        }

        watcher_contract = build_mail_watcher_contract(
            name="Watcher Test",
            template_contract=template_contract,
            email_account="test@test.com"
        )

        # Find the inherited field
        campo = next(
            (o for o in watcher_contract["outputs"] if o["name"] == "campo_extraido"),
            None
        )

        assert campo is not None
        # Inherited fields should be optional (email might not have expected attachment)
        assert campo.get("required", True) is False

    def test_mail_watcher_metadata(self):
        """Test that MailWatcher contract includes relevant metadata."""
        from client_app.app.services.asset_finishing_service import build_mail_watcher_contract

        watcher_contract = build_mail_watcher_contract(
            name="Facturas Watcher",
            template_contract={"inputs": [], "outputs": []},
            email_account="facturas@empresa.com",
            folder="INBOX/Facturas",
            filters={"subject_contains": "Factura"}
        )

        assert "metadata" in watcher_contract
        assert watcher_contract["metadata"]["type"] == "mail_watcher"
        assert watcher_contract["metadata"]["folder"] == "INBOX/Facturas"
        # Should NOT contain sensitive data like password
        assert "password" not in str(watcher_contract)


class TestMailWatcherReadmeGeneration:
    """Tests for MailWatcher-specific README generation."""

    def test_readme_includes_email_account(self):
        """Test that README mentions the monitored email account."""
        from client_app.app.services.asset_finishing_service import generate_mail_watcher_readme

        readme = generate_mail_watcher_readme(
            name="Watcher Facturas",
            email_account="facturas@empresa.com",
            folder="INBOX",
            template_name="Extractor Facturas",
            field_names=["total", "fecha", "cif"]
        )

        assert "facturas@empresa.com" in readme
        assert "INBOX" in readme
        assert "Extractor Facturas" in readme

    def test_readme_lists_extracted_fields(self):
        """Test that README lists all fields that will be extracted."""
        from client_app.app.services.asset_finishing_service import generate_mail_watcher_readme

        readme = generate_mail_watcher_readme(
            name="Test Watcher",
            email_account="test@test.com",
            folder="INBOX",
            template_name="Template Test",
            field_names=["campo1", "campo2", "campo3"]
        )

        assert "campo1" in readme
        assert "campo2" in readme
        assert "campo3" in readme

    def test_readme_includes_filters(self):
        """Test that README documents activation filters."""
        from client_app.app.services.asset_finishing_service import generate_mail_watcher_readme

        readme = generate_mail_watcher_readme(
            name="Filtered Watcher",
            email_account="test@test.com",
            folder="INBOX",
            filters={
                "subject_contains": "Factura",
                "has_attachments": True,
                "attachment_extensions": [".pdf", ".xlsx"]
            }
        )

        assert "Factura" in readme
        assert "pdf" in readme.lower() or ".pdf" in readme

    def test_readme_no_credentials_exposed(self):
        """Test that README never contains sensitive credentials."""
        from client_app.app.services.asset_finishing_service import generate_mail_watcher_readme

        readme = generate_mail_watcher_readme(
            name="Secure Watcher",
            email_account="test@test.com",
            folder="INBOX",
            template_name="Template",
            field_names=["campo1"],
            # These should NOT appear in output
            _password="secret123",
            _token="abc123token"
        )

        assert "secret123" not in readme
        assert "abc123token" not in readme
        assert "password" not in readme.lower()


class TestGetTemplateContract:
    """Tests for retrieving template contracts."""

    def test_get_template_contract_from_user_config(self):
        """Test retrieving contract from UserExtractionConfig."""
        from client_app.app.services.asset_finishing_service import get_template_contract

        # Mock session
        mock_session = MagicMock()

        # Mock UserExtractionConfig with expected_schema
        mock_config = MagicMock()
        mock_config.expected_schema = {
            "fields": [
                {"name": "total", "type": "float"},
                {"name": "fecha", "type": "date"}
            ]
        }
        mock_session.get.return_value = mock_config

        contract = get_template_contract(
            session=mock_session,
            template_id="template-123"
        )

        assert contract is not None
        assert "outputs" in contract

    def test_get_template_contract_not_found(self):
        """Test behavior when template doesn't exist."""
        from client_app.app.services.asset_finishing_service import get_template_contract

        mock_session = MagicMock()
        mock_session.get.return_value = None

        contract = get_template_contract(
            session=mock_session,
            template_id="nonexistent"
        )

        assert contract is None


class TestMailWatcherSealing:
    """Integration tests for full MailWatcher sealing process."""

    def test_seal_mail_watcher_creates_combined_contract(self):
        """Test that sealing a MailWatcher produces combined contract."""
        from client_app.app.services.asset_finishing_service import (
            AssetFinishingService,
            build_mail_watcher_contract
        )

        # Mock session and script
        mock_session = MagicMock()
        mock_script = MagicMock()
        mock_script.id = 1
        mock_script.source_module = 'mail_watcher'
        mock_script.source_metadata = {
            'extraction_template_id': 'template-abc',
            'email_account': 'test@test.com',
            'folder': 'INBOX'
        }
        mock_session.get.return_value = mock_script

        # Mock template contract retrieval
        with patch(
            'client_app.app.services.asset_finishing_service.get_template_contract'
        ) as mock_get:
            mock_get.return_value = {
                "inputs": [],
                "outputs": [
                    {"name": "total", "type": "float"}
                ]
            }

            service = AssetFinishingService(session=mock_session)

            # Call seal_mail_watcher
            result = service.seal_mail_watcher(script_id=1)

            # Verify contract was built and assigned
            assert mock_script.ui_contract is not None
            output_names = [o["name"] for o in mock_script.ui_contract["outputs"]]
            assert "email_sender" in output_names
            assert "total" in output_names
