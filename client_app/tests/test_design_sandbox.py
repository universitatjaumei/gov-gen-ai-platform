# client_app/tests/test_design_sandbox.py
"""
Test TDD for Design Sandbox Service.
Prompt #3 BIS: Sandbox de Datos en Diseño (Carga de Muestras).

Tests the design-time file management for testing scripts with sample files.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from client_app.app.services.design_sandbox_service import DesignSandboxService
from automatia_shared.contracts.ui_contract import UIContract, InputDefinition, InputType


class TestDesignSandboxService:
    """Tests for DesignSandboxService."""

    @pytest.fixture
    def temp_sandbox_dir(self, tmp_path):
        """Create a temporary sandbox directory for testing."""
        sandbox_dir = tmp_path / "sandbox"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        yield sandbox_dir
        # Cleanup
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)

    @pytest.fixture
    def service(self, temp_sandbox_dir):
        """Create a DesignSandboxService instance with temp directory."""
        return DesignSandboxService(base_path=temp_sandbox_dir)

    def test_sandbox_maps_file_path_to_variable(self, service):
        """Test that uploaded files are correctly mapped to contract variables."""
        script_id = "test-script-123"

        # 1. Simulate uploading a test file
        file_content = b"Contenido de prueba"
        file_name = "datos.xlsx"
        local_path = service.save_test_file(script_id, file_name, file_content)

        # 2. Define a contract that requires a file input
        contract = UIContract(inputs=[
            InputDefinition(name="excel_input", label="Excel Input", type=InputType.FILE)
        ])

        # 3. Validate that the execution environment receives the correct path
        env_vars = service.prepare_test_environment(script_id, contract)

        assert "excel_input" in env_vars
        assert env_vars["excel_input"] == local_path
        assert "sandbox" in env_vars["excel_input"]

    def test_cleanup_sandbox(self, service):
        """Test that sandbox cleanup removes all files for a script."""
        script_id = "test-to-clean"
        service.save_test_file(script_id, "tmp.txt", b"abc")

        # Verify file exists
        sandbox_path = service.get_sandbox_path(script_id)
        assert sandbox_path.exists()

        # Cleanup
        service.clear_sandbox(script_id)
        assert not service.get_sandbox_path(script_id).exists()

    def test_save_multiple_files(self, service):
        """Test saving multiple files for FILES type input."""
        script_id = "multi-file-test"

        # Save multiple files
        path1 = service.save_test_file(script_id, "file1.pdf", b"PDF content 1")
        path2 = service.save_test_file(script_id, "file2.pdf", b"PDF content 2")

        # Both paths should exist
        assert Path(path1).exists()
        assert Path(path2).exists()

        # Create contract with FILES type
        contract = UIContract(inputs=[
            InputDefinition(name="pdf_files", label="PDF Files", type=InputType.FILES)
        ])

        # Prepare environment - should get list of files
        env_vars = service.prepare_test_environment(script_id, contract)

        assert "pdf_files" in env_vars
        # FILES type should return a list
        assert isinstance(env_vars["pdf_files"], list)
        assert len(env_vars["pdf_files"]) == 2

    def test_get_sandbox_path(self, service):
        """Test that sandbox path is constructed correctly."""
        script_id = "path-test-123"
        path = service.get_sandbox_path(script_id)

        assert script_id in str(path)
        assert isinstance(path, Path)

    def test_list_sandbox_files(self, service):
        """Test listing all files in a script's sandbox."""
        script_id = "list-test"

        # Save some files
        service.save_test_file(script_id, "doc1.pdf", b"content1")
        service.save_test_file(script_id, "doc2.xlsx", b"content2")

        # List files
        files = service.list_sandbox_files(script_id)

        assert len(files) == 2
        filenames = [f["name"] for f in files]
        assert "doc1.pdf" in filenames
        assert "doc2.xlsx" in filenames

    def test_empty_sandbox_returns_empty_list(self, service):
        """Test that listing empty sandbox returns empty list."""
        files = service.list_sandbox_files("nonexistent-script")
        assert files == []

    def test_sanitize_filename(self, service):
        """Test that dangerous filenames are sanitized."""
        script_id = "sanitize-test"

        # Try to save with path traversal attempt
        dangerous_name = "../../../etc/passwd"
        safe_path = service.save_test_file(script_id, dangerous_name, b"test")

        # Should be sanitized - no path traversal
        assert ".." not in safe_path
        assert "etc" not in safe_path

    def test_prepare_environment_with_mixed_types(self, service):
        """Test preparing environment with mixed input types."""
        script_id = "mixed-types"

        # Save a test file
        service.save_test_file(script_id, "input.csv", b"csv,data")

        # Contract with mixed types
        contract = UIContract(inputs=[
            InputDefinition(name="csv_file", label="CSV File", type=InputType.FILE),
            InputDefinition(name="user_name", label="User Name", type=InputType.STR),
            InputDefinition(name="count", label="Count", type=InputType.INT),
        ])

        env_vars = service.prepare_test_environment(script_id, contract)

        # Only FILE types should be in env_vars
        assert "csv_file" in env_vars
        assert "user_name" not in env_vars
        assert "count" not in env_vars

    def test_delete_single_file(self, service):
        """Test deleting a single file from sandbox."""
        script_id = "delete-single"

        # Save two files
        service.save_test_file(script_id, "keep.pdf", b"keep")
        service.save_test_file(script_id, "delete.pdf", b"delete")

        # Delete one
        result = service.delete_file(script_id, "delete.pdf")
        assert result is True

        # Check only one remains
        files = service.list_sandbox_files(script_id)
        assert len(files) == 1
        assert files[0]["name"] == "keep.pdf"

    def test_get_file_for_input(self, service):
        """Test getting the file path for a specific input name."""
        script_id = "input-mapping"

        # Save file with explicit input association
        service.save_test_file(
            script_id,
            "invoice.pdf",
            b"PDF content",
            input_name="documento"
        )

        # Get file for that input
        file_path = service.get_file_for_input(script_id, "documento")
        assert file_path is not None
        assert "invoice.pdf" in file_path


class TestDesignSandboxServiceEdgeCases:
    """Edge case tests for DesignSandboxService."""

    @pytest.fixture
    def service(self, tmp_path):
        return DesignSandboxService(base_path=tmp_path / "sandbox")

    def test_empty_content_file(self, service):
        """Test saving file with empty content."""
        script_id = "empty-content"
        path = service.save_test_file(script_id, "empty.txt", b"")

        assert Path(path).exists()
        assert Path(path).stat().st_size == 0

    def test_large_file_handling(self, service):
        """Test handling of larger files."""
        script_id = "large-file"
        # 1MB of data
        large_content = b"x" * (1024 * 1024)
        path = service.save_test_file(script_id, "large.bin", large_content)

        assert Path(path).exists()
        assert Path(path).stat().st_size == len(large_content)

    def test_special_characters_in_script_id(self, service):
        """Test handling script IDs with special characters."""
        script_id = "script-with-uuid-123e4567-e89b"
        path = service.save_test_file(script_id, "test.txt", b"test")

        assert Path(path).exists()

    def test_concurrent_sandbox_access(self, service):
        """Test that different scripts have isolated sandboxes."""
        script1 = "script-1"
        script2 = "script-2"

        service.save_test_file(script1, "file.txt", b"content1")
        service.save_test_file(script2, "file.txt", b"content2")

        files1 = service.list_sandbox_files(script1)
        files2 = service.list_sandbox_files(script2)

        assert len(files1) == 1
        assert len(files2) == 1

        # Read content to verify isolation (files are in the 'files' subdirectory)
        path1 = service.get_sandbox_path(script1) / "files" / "file.txt"
        path2 = service.get_sandbox_path(script2) / "files" / "file.txt"

        assert path1.read_bytes() == b"content1"
        assert path2.read_bytes() == b"content2"
