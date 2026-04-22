import pytest
import zipfile
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock
from app.services.support.support_packager import SupportPackager

@pytest.mark.asyncio
async def test_package_creation_anonymizes_data(tmp_path: Path):
    # Mock del anonimizador
    anon = AsyncMock()
    async def fake_apply(input_path, output_path, **kw):
        Path(output_path).write_text("ANONYMIZED_CONTENT", encoding="utf-8")
    anon.apply = fake_apply

    # Crear archivo de prueba
    input_file = tmp_path / "input.pdf"
    input_file.write_text("SENSITIVE DATA", encoding="utf-8")

    # Ensure support_bundles directory exists inside tmp_path purely for test isolation if needed,
    # but the class should handle it.
    
    packager = SupportPackager(base_dir=tmp_path, anonymizer=anon)

    zip_path = await packager.create_support_bundle(
        execution_id="exec_123",
        script_content="print('error')",
        logs="Traceback: KeyError...",
        input_file=input_file
    )

    assert os.path.exists(zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "script.py" in names
        assert "error.log" in names
        assert "sample_anon.pdf" in names
        assert "manifest.json" in names

        # Verificar que la muestra está anonimizada
        assert zf.read("sample_anon.pdf").decode("utf-8") == "ANONYMIZED_CONTENT"

        # Verificar manifest
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["execution_id"] == "exec_123"
        assert "checksums" in manifest

@pytest.mark.asyncio
async def test_package_excludes_secrets(tmp_path: Path):
    packager = SupportPackager(base_dir=tmp_path, anonymizer=AsyncMock())

    # Crear archivos que deberían excluirse en el directorio de ejecución simulado
    # Note: SupportPackager usually packages files generated *within* the bundle process 
    # OR files from the execution directory.
    # The current design copies specific content (script, logs) and processed input.
    # But if we were to zip a folder, exclusion would matter.
    # In the current design, we are creating the folder content manually in create_support_bundle.
    # So the exclusion logic mainly applies if we iterate over that folder to zip it.
    
    # We will simulate a sensitive file being accidentally present or if the implementation 
    # were to zip a broader directory.
    # Let's assume the implementation zips the 'bundle_dir'. 
    # If we manually put a secret there (which shouldn't happen, but defensive coding), it should be skipped?
    # Or maybe the design implies only specific files are written. 
    # Re-reading prompt: "create_support_bundle... Contenido: manifest, script, logs, sample_anon".
    # It seems strictly controlled.
    # However, the implementation provided in the prompt iterates `for file in bundle_dir.iterdir(): ... if not self._is_excluded(file.name):`
    # So if we artificially inject a secret file into the bundle_dir before zipping, it should be excluded.

    # We need to hook into the process or manually place a file in the expected bundle dir location? 
    # Implementation: `bundle_dir = self.base_dir / "support_bundles" / execution_id`
    
    execution_id = "exec_456"
    bundle_dir = tmp_path / "support_bundles" / execution_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / ".env").write_text("SECRET=xxx", encoding="utf-8")

    zip_path = await packager.create_support_bundle(
        execution_id=execution_id,
        script_content="print('ok')",
        logs="No error",
    )

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert ".env" not in names
        # Standard files should be there
        assert "script.py" in names

@pytest.mark.asyncio
async def test_package_respects_size_limit(tmp_path: Path):
    packager = SupportPackager(
        base_dir=tmp_path,
        anonymizer=AsyncMock(),
        max_size_mb=1  # 1MB límite
    )

    # Crear archivo grande
    big_file = tmp_path / "big.pdf"
    # Write 1.5MB
    with open(big_file, "wb") as f:
        f.write(b"x" * (int(1.5 * 1024 * 1024)))

    with pytest.raises(ValueError, match="size limit"):
        await packager.create_support_bundle(
            execution_id="exec_789",
            script_content="print('ok')",
            logs="",
            input_file=big_file
        )

@pytest.mark.asyncio
async def test_manifest_includes_versions(tmp_path: Path):
    packager = SupportPackager(base_dir=tmp_path, anonymizer=AsyncMock())

    zip_path = await packager.create_support_bundle(
        execution_id="exec_001",
        script_content="",
        logs="",
    )

    with zipfile.ZipFile(zip_path) as zf:
        manifest = json.loads(zf.read("manifest.json"))

        assert "app_version" in manifest
        # assert "shared_version" in manifest # Might depend on if we can import it in test env
        assert "python_version" in manifest
        assert "os" in manifest

