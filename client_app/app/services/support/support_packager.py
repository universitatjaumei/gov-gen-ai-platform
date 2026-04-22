import zipfile
import hashlib
import json
import platform
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

class SupportPackager:
    """Genera paquetes de soporte seguros para escalado."""

    EXCLUDED_PATTERNS = {".env", "credentials", ".key", ".pem", "secret", "password"}

    def __init__(
        self,
        base_dir: Path,
        anonymizer: Any,
        max_size_mb: int = 50
    ):
        self.base_dir = base_dir
        self.anonymizer = anonymizer
        self.max_size_mb = max_size_mb

    async def create_support_bundle(
        self,
        execution_id: str,
        script_content: str,
        logs: str,
        input_file: Optional[Path] = None,
    ) -> str:
        """
        Crea ZIP con contexto de fallo.

        Contenido:
        - manifest.json (metadatos, checksums)
        - script.py (código que falló)
        - error.log (logs de ejecución)
        - sample_anon.* (muestra anonimizada, si hay input)
        """
        bundle_dir = self.base_dir / "support_bundles" / execution_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        checksums = {}

        # 1. Script
        script_path = bundle_dir / "script.py"
        script_path.write_text(script_content, encoding="utf-8")
        checksums["script.py"] = self._hash_file(script_path)

        # 2. Logs
        log_path = bundle_dir / "error.log"
        log_path.write_text(logs, encoding="utf-8")
        checksums["error.log"] = self._hash_file(log_path)

        # 3. Muestra anonimizada
        sample_path = None
        if input_file and input_file.exists():
            # Verificar tamaño
            if input_file.stat().st_size > self.max_size_mb * 1024 * 1024:
                raise ValueError(f"Input file exceeds size limit of {self.max_size_mb}MB")

            sample_path = bundle_dir / f"sample_anon{input_file.suffix}"
            await self.anonymizer.apply(str(input_file), str(sample_path))
            checksums[sample_path.name] = self._hash_file(sample_path)

        # 4. Manifest
        manifest = {
            "execution_id": execution_id,
            "created_at": datetime.utcnow().isoformat(),
            "app_version": self._get_app_version(),
            "shared_version": self._get_shared_version(),
            "python_version": sys.version,
            "os": f"{platform.system()} {platform.release()}",
            "checksums": checksums,
            "anonymization_applied": sample_path is not None,
        }

        manifest_path = bundle_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # 5. Crear ZIP
        zip_path = self.base_dir / "support_bundles" / f"support_{execution_id}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for file in bundle_dir.iterdir():
                if not self._is_excluded(file.name):
                    zf.write(file, file.name)

        return str(zip_path)

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _is_excluded(self, filename: str) -> bool:
        lower = filename.lower()
        return any(p in lower for p in self.EXCLUDED_PATTERNS)

    def _get_app_version(self) -> str:
        try:
            from client_app import __version__
            return __version__
        except ImportError:
            return "unknown"
        except AttributeError:
            return "unknown"

    def _get_shared_version(self) -> str:
        try:
            from automatia_shared import __version__
            return __version__
        except ImportError:
            return "unknown"
        except AttributeError:
            return "unknown"
