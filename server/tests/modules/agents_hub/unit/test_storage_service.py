"""Tests del protocolo StorageService — TDD RED.

Estos tests deben fallar con ImportError hasta que se implemente
server/app/core/storage.py (Prompt 9C.2).
"""
import pytest


class TestFsspecStorageService:

    @pytest.fixture
    def storage(self, tmp_path):
        from server.app.core.storage import FsspecStorageService
        return FsspecStorageService(backend="file", bucket=str(tmp_path))

    @pytest.mark.asyncio
    async def test_put_and_get_roundtrip(self, storage) -> None:
        await storage.put("docs/test.pdf", b"PDF content")
        result = await storage.get("docs/test.pdf")
        assert result == b"PDF content"

    @pytest.mark.asyncio
    async def test_exists_returns_true_after_put(self, storage) -> None:
        await storage.put("docs/present.pdf", b"data")
        assert await storage.exists("docs/present.pdf") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing_key(self, storage) -> None:
        assert await storage.exists("nonexistent/file.pdf") is False

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, storage) -> None:
        await storage.put("docs/to_delete.pdf", b"data")
        await storage.delete("docs/to_delete.pdf")
        assert await storage.exists("docs/to_delete.pdf") is False

    @pytest.mark.asyncio
    async def test_get_raises_on_missing_file(self, storage) -> None:
        with pytest.raises(FileNotFoundError):
            await storage.get("nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_put_overwrites_existing_file(self, storage) -> None:
        await storage.put("docs/overwrite.pdf", b"original")
        await storage.put("docs/overwrite.pdf", b"updated")
        result = await storage.get("docs/overwrite.pdf")
        assert result == b"updated"

    @pytest.mark.asyncio
    async def test_put_creates_intermediate_directories(self, storage) -> None:
        await storage.put("nested/deep/dir/file.pdf", b"data")
        assert await storage.exists("nested/deep/dir/file.pdf") is True

    @pytest.mark.asyncio
    async def test_put_and_get_binary_content(self, storage) -> None:
        binary = bytes(range(256))
        await storage.put("bin/data.bin", binary)
        assert await storage.get("bin/data.bin") == binary


class TestGetStorageService:

    def test_returns_fsspec_service_with_env_vars(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("STORAGE_BACKEND", "file")
        monkeypatch.setenv("STORAGE_BUCKET", str(tmp_path))
        from server.app.core import storage as storage_module
        storage_module._build_storage_service.cache_clear()
        service = storage_module.get_storage_service()
        from server.app.core.storage import FsspecStorageService
        assert isinstance(service, FsspecStorageService)

    def test_same_instance_returned_on_repeated_calls(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("STORAGE_BACKEND", "file")
        monkeypatch.setenv("STORAGE_BUCKET", str(tmp_path))
        from server.app.core import storage as storage_module
        storage_module._build_storage_service.cache_clear()
        s1 = storage_module.get_storage_service()
        s2 = storage_module.get_storage_service()
        assert s1 is s2

    def test_protocol_satisfied(self, monkeypatch, tmp_path) -> None:
        """FsspecStorageService debe satisfacer el protocolo StorageService."""
        monkeypatch.setenv("STORAGE_BACKEND", "file")
        monkeypatch.setenv("STORAGE_BUCKET", str(tmp_path))
        from server.app.core import storage as storage_module
        storage_module._build_storage_service.cache_clear()
        service = storage_module.get_storage_service()
        from server.app.core.storage import StorageService
        assert isinstance(service, StorageService)
