"""
Tests for automatia_shared.core module.
Tests the core utilities moved from app/core.
"""

import pytest
import tempfile
from pathlib import Path


class TestSecurityModule:
    """Tests for security.py"""

    def test_security_auditor_safe_code(self):
        """Verify safe code passes audit."""
        from automatia_shared.core.security import audit_code

        safe_code = '''
import re
import fitz

def extract(filename):
    with fitz.open(filename) as doc:
        return doc[0].get_text()
'''
        result = audit_code(safe_code)
        assert result['status'] == 'SAFE'
        assert len(result['reasons']) == 0

    def test_security_auditor_detects_unsafe_imports(self):
        """Verify unsafe imports are detected."""
        from automatia_shared.core.security import audit_code

        unsafe_code = '''
import os
import subprocess

def execute(cmd):
    return subprocess.run(cmd)
'''
        result = audit_code(unsafe_code)
        assert result['status'] == 'CRITICAL'
        assert any('os' in r for r in result['reasons'])
        assert any('subprocess' in r for r in result['reasons'])

    def test_security_auditor_detects_absolute_paths(self):
        """Verify absolute paths are detected."""
        from automatia_shared.core.security import audit_code

        # Using raw string with escaped backslashes as they would appear in source code
        code_with_path = r'''
path = "C:\\Users\\data\\file.txt"
'''
        result = audit_code(code_with_path)
        assert result['status'] == 'CRITICAL'
        assert any('Windows' in r or 'Ruta' in r for r in result['reasons'])

    def test_validate_code_ast_raises_on_critical(self):
        """Verify validate_code_ast raises SecurityException."""
        from automatia_shared.core.security import validate_code_ast, SecurityException

        unsafe_code = "import os"
        with pytest.raises(SecurityException):
            validate_code_ast(unsafe_code)


class TestExecutionManager:
    """Tests for execution_manager.py"""

    def test_run_manifest_save_load(self):
        """Verify RunManifest can save and load."""
        from automatia_shared.core.execution_manager import RunManifest

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "test_manifest.json"
            manifest = RunManifest(manifest_path)
            manifest.data['run_id'] = 'test_123'
            manifest.data['status'] = 'running'
            manifest.save()

            # Reload
            manifest2 = RunManifest(manifest_path)
            manifest2.load()
            assert manifest2.data['run_id'] == 'test_123'
            assert manifest2.data['status'] == 'running'

    def test_execution_path_manager_create_run(self):
        """Verify ExecutionPathManager creates run directories."""
        from automatia_shared.core.execution_manager import ExecutionPathManager

        # Use custom base to avoid polluting home dir
        manager = ExecutionPathManager(app_name='test_automatia')
        run_id = manager.create_run('TEST_TASK')

        assert run_id.startswith('run_')

        # Verify directories exist
        run_dir = manager.get_run_dir('TEST_TASK', run_id)
        assert run_dir.exists()
        assert (run_dir / 'inputs').exists()
        assert (run_dir / 'outputs').exists()
        assert (run_dir / 'scripts').exists()

    def test_save_script_version(self):
        """Verify script versioning works."""
        from automatia_shared.core.execution_manager import ExecutionPathManager

        manager = ExecutionPathManager(app_name='test_automatia')
        run_id = manager.create_run('SCRIPT_TEST')

        script_content = "def extract(): return {}"
        path = manager.save_script_version(run_id, script_content)

        assert Path(path).exists()
        with open(path, 'r') as f:
            assert f.read() == script_content


class TestI18nModule:
    """Tests for i18n.py"""

    def test_i18n_manager_default_locale(self):
        """Verify default locale is Spanish."""
        from automatia_shared.core.i18n import I18nManager

        manager = I18nManager()
        assert manager.locale == 'es'

    def test_i18n_fallback_to_key(self):
        """Verify missing keys return the key itself."""
        from automatia_shared.core.i18n import t

        result = t('nonexistent_key')
        assert result == 'nonexistent_key'

    def test_i18n_set_locale(self):
        """Verify locale can be changed."""
        from automatia_shared.core.i18n import i18n

        original = i18n.locale
        i18n.set_locale('en')
        assert i18n.locale == 'en'
        i18n.set_locale(original)  # Reset


class TestDataConsolidator:
    """Tests for consolidator.py"""

    def test_filter_by_schema(self):
        """Verify schema filtering works."""
        from automatia_shared.core.consolidator import DataConsolidator

        raw_data = {
            'invoice_number': 'INV-001',
            'amount': 100.50,
            'noise_field': 'should be removed',
            'extra': 'also removed'
        }
        schema = ['invoice_number', 'amount']

        result = DataConsolidator.filter_by_schema(raw_data, schema)
        assert 'invoice_number' in result
        assert 'amount' in result
        assert 'noise_field' not in result
        assert 'extra' not in result

    def test_consolidate_result_structure(self):
        """Verify consolidation returns proper structure."""
        from automatia_shared.core.consolidator import DataConsolidator

        data = {'field1': 'value1'}
        result = DataConsolidator.consolidate_result(
            data,
            source_engine='gpt-4',
            confidence_score=0.95
        )

        assert result['status'] == 'ok'
        assert result['data'] == data
        assert result['meta']['engine'] == 'gpt-4'
        assert result['meta']['confidence'] == 0.95

    def test_merge_multiple_sources(self):
        """Verify source merging works."""
        from automatia_shared.core.consolidator import DataConsolidator

        sources = [
            {'field1': 'value1'},
            {'field2': 'value2'},
            {'data': {'field3': 'value3'}, 'meta': {}}
        ]

        result = DataConsolidator.merge_multiple_sources(sources)
        assert result['field1'] == 'value1'
        assert result['field2'] == 'value2'
        assert result['field3'] == 'value3'


class TestCoreImports:
    """Verify all core modules are importable."""

    def test_import_reader(self):
        """Verify reader functions import."""
        from automatia_shared.core import (
            extraer_texto_dual,
            extraer_texto_pyMuPDF,
            extraer_texto_pdfplumber,
        )
        assert all([extraer_texto_dual, extraer_texto_pyMuPDF, extraer_texto_pdfplumber])

    def test_import_pdf_reader(self):
        """Verify PdfReaderDual imports."""
        from automatia_shared.core import PdfReaderDual
        assert PdfReaderDual is not None

    def test_import_security(self):
        """Verify security module imports."""
        from automatia_shared.core import (
            SecurityAuditor,
            SecurityException,
            audit_code,
            validate_code_ast,
        )
        assert all([SecurityAuditor, SecurityException, audit_code, validate_code_ast])

    def test_import_execution_manager(self):
        """Verify execution manager imports."""
        from automatia_shared.core import (
            ExecutionLock,
            RunManifest,
            ExecutionPathManager,
        )
        assert all([ExecutionLock, RunManifest, ExecutionPathManager])

    def test_import_i18n(self):
        """Verify i18n imports."""
        from automatia_shared.core import i18n, t, I18nManager
        assert all([i18n, t, I18nManager])

    def test_import_consolidator(self):
        """Verify consolidator imports."""
        from automatia_shared.core import DataConsolidator
        assert DataConsolidator is not None
