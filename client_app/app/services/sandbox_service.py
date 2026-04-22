# client_app/app/services/sandbox_service.py
"""
Sandbox Execution Service for Client (On-Premise).

Provides secure, jailed execution of AI-generated extraction scripts.
Uses process isolation and AST validation for security.
"""
import asyncio
import importlib.util
import sys
import os
import shutil
import traceback
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ProcessPoolExecutor

from automatia_shared.core.execution_manager import ExecutionPathManager
from automatia_shared.core.security import validate_code_ast, SecurityException
from client_app.app.services.sandbox_worker import _run_jailed_process

class IntegrityError(SecurityException):
    """Error de verificación de integridad (hash o firma)."""
    pass

class SandboxExecutionService:
    def __init__(self, execution_path_manager: ExecutionPathManager, public_key: Optional[bytes] = None):
        self.path_manager = execution_path_manager
        self._public_key = public_key
        # POOL LAZY: Se crea solo cuando se necesita para evitar problemas de shutdown en Windows
        self._executor = None

    def _get_executor(self) -> ProcessPoolExecutor:
        """Lazy initialization of ProcessPoolExecutor."""
        if self._executor is None:
            try:
                print("[Sandbox] Initializing ProcessPoolExecutor...")
                self._executor = ProcessPoolExecutor(max_workers=10)
                print("[Sandbox] ProcessPoolExecutor initialized successfully")
            except Exception as init_err:
                print(f"[Sandbox] ❌ Failed to initialize ProcessPoolExecutor: {init_err}")
                import traceback
                traceback.print_exc()
                raise
        return self._executor

    def shutdown(self):
        """Clean shutdown of process pool - call this on app exit."""
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass
            self._executor = None

    def __del__(self):
        """Cleanup process pool on destruction"""
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def validate_safe_code(self, code: str) -> bool:
        """
        Valida que el código no contenga llamadas o módulos prohibidos
        mediante análisis estático del AST.
        """
        try:
            return validate_code_ast(code)
        except SecurityException as e:
            print(f"[Sandbox] Security Check Failed: {e}")
            return False

    def validate_integrity(
        self,
        code: str,
        expected_hash: Optional[str] = None,
        expected_sig: Optional[bytes] = None
    ) -> bool:
        """Verifica integridad del código."""
        if self._public_key:
            if expected_sig is None:
                raise IntegrityError("Signature required: public key is configured")

            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                public_key = Ed25519PublicKey.from_public_bytes(self._public_key)
                public_key.verify(expected_sig, code.encode())
            except Exception as e:
                raise IntegrityError(f"Invalid signature: {e}")

        if expected_hash:
            actual_hash = hashlib.sha256(code.encode()).hexdigest()
            if actual_hash != expected_hash:
                raise IntegrityError(
                    f"Hash mismatch: expected {expected_hash[:16]}..., "
                    f"got {actual_hash[:16]}..."
                )

        return True

    async def execute_in_sandbox(self, code: str, file_paths: List[str], execution_id: str, target_function: str = "extraer_datos") -> Dict[str, Any]:
        """
        Ejecuta el código proporcionado en un entorno aislado (jail).
        """
        # 0. Validate
        try:
            validate_code_ast(code)
        except SecurityException as e:
            return {"success": False, "error": f"Security Violation: {str(e)}"}

        # 1. Prepare Paths
        try:
            exec_path = self.path_manager.get_execution_path(execution_id)
            input_dir = exec_path / "input"
            sandbox_dir = exec_path / "sandbox"
            output_dir = exec_path / "output"

            input_dir.mkdir(parents=True, exist_ok=True)
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 2. Copy Input Files
            requested_files = []
            for fp in file_paths:
                src = Path(fp).resolve()
                if src.exists():
                    dest = (input_dir / src.name).resolve()
                    requested_files.append(src.name)

                    if src == dest:
                        continue

                    import time
                    for i in range(3):
                        try:
                            shutil.copy2(src, dest)
                            break
                        except (PermissionError, OSError) as e:
                            if i == 2: raise e
                            time.sleep(1.0)

            # 3. Write Script
            import uuid
            script_name = f"script_{execution_id}_{uuid.uuid4().hex[:8]}.py"
            script_path = sandbox_dir / script_name
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 4. Execute in Persistent Process Pool
            loop = asyncio.get_running_loop()

            try:
                executor = self._get_executor()
                task = loop.run_in_executor(
                    executor,
                    _run_jailed_process,
                    str(script_path),
                    str(input_dir),
                    target_function,
                    requested_files
                )

                result = await asyncio.wait_for(task, timeout=120.0)
                return result

            except asyncio.TimeoutError:
                return {"success": False, "error": "Execution Timeout (120s exceeded)."}
            except Exception as exec_err:
                traceback.print_exc()
                return {"success": False, "error": f"Executor Error: {str(exec_err)}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": f"Infrastructure Error: {str(e)}"}

    async def execute_script_async(self, code: str, file_path: str, execution_id: str) -> Dict[str, Any]:
        return await self.execute_in_sandbox(code, [file_path], execution_id)

    async def execute(
        self,
        code: str,
        input_files: List[str] = None,
        timeout: int = 120,
        target_function: str = "extraer_datos"
    ) -> Dict[str, Any]:
        import uuid
        execution_id = f"wf_{uuid.uuid4().hex[:12]}"

        result = await self.execute_in_sandbox(
            code=code,
            file_paths=input_files or [],
            execution_id=execution_id,
            target_function=target_function
        )

        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data"),
                "output_files": [],
                "preview": str(result.get("data", ""))[:500]
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "output_files": []
            }

# === Singleton Instance ===
sandbox_service = SandboxExecutionService(ExecutionPathManager())
