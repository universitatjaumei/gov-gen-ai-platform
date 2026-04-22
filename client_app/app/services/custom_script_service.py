
"""
Custom Script Service - Gestión de scripts personalizados.
CS-02 implementation.
Prompt #3: Integrates AssetFinishingService for automatic contract generation.
"""
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict

from automatia_shared.security.ast_validator import ASTSecurityValidator, ValidationResult

from client_app.app.database.db import client_engine
from client_app.app.database.models import CustomScript, CustomScriptExecution

logger = logging.getLogger(__name__)

from client_app.app.services.config_service import config_service

# Paths are now managed by config_service
SCRIPTS_DIR = config_service.get_path("CUSTOM_SCRIPTS_DIR")
DOCS_DIR = config_service.get_path("CUSTOM_DOCS_DIR")

@dataclass
class PromotionResult:
    """Result of script promotion attempt."""
    success: bool
    new_status: Optional[str]
    validation_result: Optional[ValidationResult]
    message: str

class CustomScriptService:
    """
    Servicio encargado de la gestión integral de scripts personalizados (Custom Scripts).
    Implementa persistencia híbrida (DB + Sistema de archivos) y orquestación con
    AssetFinishingService para el sellado atómico de contratos.
    """
    _instance = None

    def __new__(cls):
        """
        Garantiza una única instancia del servicio.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Prompt #3: Initialize finishing service attribute
            cls._instance.finishing_service = None
            # Initialize paths from config
            cls._instance.scripts_dir = config_service.get_path("CUSTOM_SCRIPTS_DIR")
            cls._instance.docs_dir = config_service.get_path("CUSTOM_DOCS_DIR")
            cls._instance.sandbox_enabled = config_service.get_bool("SANDBOX_STRICT_MODE")
        return cls._instance

    def calculate_code_hash(self, code: str) -> str:
        """Calculates SHA256 code hash."""
        return hashlib.sha256(code.encode()).hexdigest()

    async def create_script(
        self,
        name: str,
        user_prompt: str,
        code: str,
        description: str = "",
        required_libraries: List[str] = None,
        input_type: str = "file",
        input_extensions: List[str] = None,
        input_description: str = "",
        output_type: str = "file",
        output_description: str = "",
        tags: List[str] = None,
        # Prompt 7 Fields
        ui_contract: Dict = None,
        execution_mode: str = "local",
        visualization_config: Dict = None
    ) -> CustomScript:
        """
        Crea un nuevo script personalizado con persistencia híbrida y sincronización
        con la biblioteca de scripts.

        Pasos principales:
        1. Crea el registro en la base de datos CustomScript.
        2. Guarda el código fuente (.py) y la documentación (.md) en el sistema de archivos.
        3. Realiza la doble escritura (Dual Write) en la ScriptLibrary general.
        4. Invoca al AssetFinishingService para el sellado (inferencia de contrato y README).

        Args:
            name: Nombre del script.
            user_prompt: El prompt original usado para generar el script.
            code: El código fuente Python generado.
            description: Descripción técnica.
            ...otros parámetros de configuración de entrada/salida y UI.

        Returns:
            La instancia de CustomScript creada y persistida.
        """
        
        # Prepare Filenames
        sanitized_name = "".join(x for x in name if x.isalnum() or x in (' ', '_', '-')).replace(" ", "_").lower()
        
        script = CustomScript(
            name=name,
            user_prompt=user_prompt,
            # code is set temporarily for hash but not persisted as primary source in full hybrid mode
            # We keep it in DB column for now as fallback/compat but will overwrite it
            code=code, 
            code_hash=self.calculate_code_hash(code),
            description=description, # Can be moved to doc
            required_libraries=required_libraries or [],
            input_type=input_type,
            input_extensions=input_extensions or [],
            input_description=input_description,
            output_type=output_type,
            output_description=output_description,
            tags=tags or [],
            status="draft",
            ui_contract=ui_contract or {},
            execution_mode=execution_mode,
            visualization_config=visualization_config or {},
            script_path="", 
            doc_path=""
        )
        
        async with AsyncSession(client_engine) as session:
            session.add(script)
            await session.flush() # Get ID
            await session.refresh(script)
            
            # Save Files
            filename_py = f"{script.id}_{sanitized_name}.py"
            filename_md = f"{script.id}_{sanitized_name}.md"
            
            with open(SCRIPTS_DIR / filename_py, "w", encoding="utf-8") as f:
                f.write(code)
                
            doc_content = f"# {name}\n\n{description}\n"
            with open(DOCS_DIR / filename_md, "w", encoding="utf-8") as f:
                f.write(doc_content)
                
            script.script_path = filename_py
            script.doc_path = filename_md
            
            session.add(script)
            await session.commit()
            await session.refresh(script)
            
            # PROMPT 8: Sync with Script Library (Dual Write)
            library_script = None
            try:
                from client_app.app.services.script_library_service import script_library_service
                library_script = await script_library_service.add_script(
                    source_module='custom',
                    name=script.name,
                    code=code,
                    description=script.description or "",
                    tags=script.tags or [],
                    ui_contract=script.ui_contract,
                    data_contract=script.data_contract or {},
                    source_automation_id=script.id,
                    source_metadata={'execution_mode': execution_mode},
                    user_prompt=user_prompt
                )
            except Exception as e:
                 print(f"[CustomScriptService] Warning: Failed to sync to library: {e}")
            
            # PROMPT 3: Atomic Seal - Generate contract and documentation
            # Seal the ScriptLibrary record (not CustomScript)
            if self.finishing_service and library_script:
                try:
                    logger.info(f"Sealing library script {library_script.id} for custom script {script.id} ({script.name})...")
                    
                    # Create a new session for the finishing service
                    
                    # Create a new session for the finishing service
                    async with AsyncSession(client_engine) as seal_session:
                        # Create finishing service instance with this session
                        from client_app.app.services.asset_finishing_service import AssetFinishingService
                        finishing_svc = AssetFinishingService(session=seal_session)
                        
                        sealed_script = await finishing_svc.seal_resource(
                            script_id=library_script.id
                        )
                        logger.info(
                            f"Library script {library_script.id} sealed successfully. "
                            f"Contract inputs: {len(sealed_script.ui_contract.get('inputs', []))}"
                        )
                        
                        # Update the CustomScript with the generated contract
                        script.ui_contract = sealed_script.ui_contract
                        await session.commit()
                        await session.refresh(script)
                        
                except Exception as e:
                    logger.error(
                        f"Failed to seal library script for custom script {script.id}: {e}",
                        exc_info=True
                    )
                    # Don't fail the creation, just log the error

            return script

    async def get_script(self, script_id: int) -> Optional[CustomScript]:
        """
        Recupera un script por su ID, cargando su código fuente desde el sistema de archivos.

        Args:
            script_id: ID del script en la DB.

        Returns:
            Objeto CustomScript con el campo .code poblado desde disco, o None si no existe.
        """
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if script:
                # Load Code from Disk
                if script.script_path:
                    try:
                        file_path = SCRIPTS_DIR / script.script_path
                        if file_path.exists():
                            with open(file_path, "r", encoding="utf-8") as f:
                                script.code = f.read()
                    except Exception as e:
                        script.code = f"# Error loading script: {e}"
                
                # Load Doc (Optional, maybe for specific view)
                # if script.doc_path: ...
                
            return script

    async def get_all_scripts(
        self, 
        status: str = None, 
        search: str = None
    ) -> List[CustomScript]:
        """
        Recupera todos los scripts, aplicando filtros opcionales de estado y búsqueda por nombre.
        """
        async with AsyncSession(client_engine) as session:
            query = select(CustomScript)
            
            if status:
                query = query.where(CustomScript.status == status)
            
            if search:
                query = query.where(CustomScript.name.ilike(f"%{search}%"))
                
            result = await session.execute(query)
            return result.scalars().all()

    async def update_script(self, script_id: int, **kwargs) -> CustomScript:
        """
        Actualiza los campos y archivos de un script existente.
        Si el código cambia, se dispara un re-sellado atómico para actualizar el contrato.
        """
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if not script:
                raise ValueError(f"Script {script_id} not found")
            
            # Track if code changed (for sealing)
            code_changed = "code" in kwargs
            
            # Update DB Fields
            for key, value in kwargs.items():
                if hasattr(script, key) and key not in ['code', 'description']:
                    setattr(script, key, value)
            
            # Handle Hybrid Update
            if "code" in kwargs and script.script_path:
                 code = kwargs["code"]
                 script.code_hash = self.calculate_code_hash(code)
                 script.code = code # Update DB copy too for now
                 with open(SCRIPTS_DIR / script.script_path, "w", encoding="utf-8") as f:
                    f.write(code)
            
            if "description" in kwargs and script.doc_path:
                 desc = kwargs["description"]
                 script.description = desc
                 # Read existing doc to preserve prompt? Or just overwrite?
                 # ideally parse MD, but simple overwrite for prototype:
                 with open(DOCS_DIR / script.doc_path, "w", encoding="utf-8") as f:
                    f.write(f"# {script.name}\n\n{desc}\n")

            script.updated_at = datetime.utcnow()
            session.add(script)
            await session.commit()
            await session.refresh(script)
            
            # PROMPT 8: Sync with Script Library (Dual Write)
            try:
                from client_app.app.services.script_library_service import script_library_service
                # Only sync changed fields
                sync_kwargs = {}
                if "code" in kwargs: sync_kwargs["code"] = kwargs["code"]
                if "description" in kwargs: sync_kwargs["description"] = kwargs["description"]
                if "name" in kwargs: sync_kwargs["name"] = kwargs["name"]
                
                if sync_kwargs:
                    await script_library_service.update_script_from_source(
                        source_module='custom',
                        source_id=script.id,
                        **sync_kwargs
                    )
            except Exception as e:
                 print(f"[CustomScriptService] Warning: Failed to sync update to library: {e}")
            
            # PROMPT 3: Re-seal if code changed
            # Find and seal the corresponding ScriptLibrary record
            if code_changed and self.finishing_service:
                try:
                    logger.info(f"Re-sealing library script for custom script {script.id} due to code change...")
                    from client_app.app.database.models import ScriptLibrary
                    
                    # Find the library script
                    
                    # Find the library script
                    async with AsyncSession(client_engine) as seal_session:
                        # Query for library script by source_automation_id
                        query = select(ScriptLibrary).where(
                            ScriptLibrary.source_module == 'custom',
                            ScriptLibrary.source_automation_id == script.id
                        )
                        result = await seal_session.execute(query)
                        library_script = result.scalar_one_or_none()
                        
                        if library_script:
                            # Create finishing service instance with this session
                            from client_app.app.services.asset_finishing_service import AssetFinishingService
                            finishing_svc = AssetFinishingService(session=seal_session)
                            
                            sealed_script = await finishing_svc.seal_resource(
                                script_id=library_script.id
                            )
                            logger.info(
                                f"Library script {library_script.id} re-sealed successfully. "
                                f"Contract inputs: {len(sealed_script.ui_contract.get('inputs', []))}"
                            )
                            
                            # Update the CustomScript with the refreshed contract
                            script.ui_contract = sealed_script.ui_contract
                            await session.commit()
                            await session.refresh(script)
                        else:
                            logger.warning(f"No library script found for custom script {script.id}")
                            
                except Exception as e:
                    logger.error(
                        f"Failed to re-seal library script for custom script {script.id}: {e}",
                        exc_info=True
                    )

            return script

    async def delete_script(self, script_id: int) -> bool:
        """
        Elimina un script tanto de la base de datos como del sistema de archivos.
        """
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if not script:
                return False
            
            # Delete files
            if script.script_path:
                try: (SCRIPTS_DIR / script.script_path).unlink(missing_ok=True)
                except: pass
            if script.doc_path:
                try: (DOCS_DIR / script.doc_path).unlink(missing_ok=True)
                except: pass

            await session.delete(script)
            await session.commit()
            return True

    async def toggle_favorite(self, script_id: int) -> bool:
        """
        Alterna el estado de 'favorito' de un script.
        """
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if not script:
                return False
            
            script.is_favorite = not script.is_favorite
            session.add(script)
            await session.commit()
            return True

    async def duplicate_script(self, script_id: int, new_name: str) -> CustomScript:
        """
        Crea un duplicado de un script existente, incluyendo sus archivos físicos.
        Utiliza create_script internamente para asegurar la consistencia del sellado.
        """
        async with AsyncSession(client_engine) as session:
            original = await session.get(CustomScript, script_id)
            if not original:
                raise ValueError(f"Script {script_id} not found")
            
            # Logic needs update for hybrid dupe (copy files) using create_script likely best
            # reusing create_script to handle file creation:
            
            # Need to load code if not in memory
            code = original.code
            if original.script_path and (not code or code.startswith('# Error')):
                 try: 
                     with open(SCRIPTS_DIR / original.script_path, 'r') as f: code = f.read()
                 except: pass

            return await self.create_script(
                name=new_name,
                user_prompt=original.user_prompt,
                code=code,
                description=original.description,
                required_libraries=original.required_libraries,
                input_type=original.input_type,
                input_extensions=original.input_extensions,
                output_type=original.output_type,
                tags=original.tags,
                ui_contract=original.ui_contract,
                execution_mode=original.execution_mode,
                visualization_config=original.visualization_config
            )

    async def escalate_script(
        self,
        script_id: int,
        reason: str,
        client_notes: str = None
    ) -> str:
        """
        Marca un script como escalado para revisión por el Partner.

        Args:
            script_id: ID del script.
            reason: Motivo del escalonamiento.
            client_notes: Notas adicionales del cliente.

        Returns:
            Un identificador de ticket de escalonamiento.
        """
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if not script:
                raise ValueError(f"Script {script_id} not found")
            
            script.status = "escalated"
            session.add(script)
            await session.commit()
            
            return f"esc_{script_id}_{datetime.utcnow().timestamp()}"

    # === EXECUTION LOGGING ===

    async def log_execution_start(
        self, 
        script_id: int, 
        input_files: List[str]
    ) -> CustomScriptExecution:
        """
        Registra el inicio de la ejecución de un script en la tabla de auditoría.
        """
        execution = CustomScriptExecution(
            script_id=script_id,
            input_files=input_files,
            started_at=datetime.utcnow(),
            status="running"
        )
        
        async with AsyncSession(client_engine) as session:
            session.add(execution)
            await session.commit()
            await session.refresh(execution)
            return execution

    async def log_execution_end(
        self,
        execution_id: int,
        status: str,
        output_files: List[str] = None,
        error_message: str = None,
        output_preview: str = None,
        duration_ms: int = 0
    ):
        """
        Registra la finalización de un script y actualiza las métricas de rendimiento
        del script (contador de éxitos, tiempo medio, etc.).
        """
        async with AsyncSession(client_engine) as session:
            execution = await session.get(CustomScriptExecution, execution_id)
            if not execution:
                return
            
            execution.status = status
            execution.completed_at = datetime.utcnow()
            execution.output_files = output_files or []
            execution.error_message = error_message
            execution.output_preview = output_preview
            # If duration passed is 0, calculate it
            if duration_ms == 0 and execution.started_at:
                execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            else:
                execution.duration_ms = duration_ms
            
            session.add(execution)
            
            # Update Script Metrics
            script = await session.get(CustomScript, execution.script_id)
            if script:
                script.execution_count += 1
                script.last_executed = execution.completed_at
                if status == "success":
                    script.success_count += 1
                
                total_duration = (script.avg_execution_time_ms * (script.execution_count - 1)) + execution.duration_ms
                script.avg_execution_time_ms = int(total_duration / script.execution_count)
                
                session.add(script)

            await session.commit()
            
    async def get_execution_history(
        self, 
        script_id: int, 
        limit: int = 20
    ) -> List[CustomScriptExecution]:
        """
        Recupera el historial de ejecuciones reciente para un script específico.
        """
        async with AsyncSession(client_engine) as session:
            query = select(CustomScriptExecution)\
                .where(CustomScriptExecution.script_id == script_id)\
                .order_by(desc(CustomScriptExecution.started_at))\
                .limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()

    async def promote_script(
        self,
        script_id: int,
        target_status: str,
        allow_network: bool = False
    ) -> PromotionResult:
        """
        Promociona un script a un nuevo estado (ej. 'validated' o 'published') realizande
        previamente una auditoría de seguridad AST.

        Args:
            script_id: ID del script a promocionar.
            target_status: Estado destino deseado.
            allow_network: Si se permite explícitamente el uso de red en la validación.

        Returns:
            PromotionResult con el éxito de la operación y detalles de la validación.
        """
        # Valid transitions
        valid_transitions = {
            'draft': ['validated'],
            'validated': ['published', 'draft'],  # Can demote
            'published': ['draft']  # Can unpublish
        }
        
        async with AsyncSession(client_engine) as session:
            script = await session.get(CustomScript, script_id)
            if not script:
                return PromotionResult(
                    success=False,
                    new_status=None,
                    validation_result=None,
                    message=f"Script {script_id} not found"
                )
            
            # Check valid transition
            if target_status not in valid_transitions.get(script.status, []):
                return PromotionResult(
                    success=False,
                    new_status=script.status,
                    validation_result=None,
                    message=f"Invalid transition from '{script.status}' to '{target_status}'"
                )
            
            # Validate security if promoting (not demoting)
            if target_status in ['validated', 'published']:
                # Load code from disk
                code = script.code
                if script.script_path:
                    try:
                        with open(SCRIPTS_DIR / script.script_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception as e:
                        return PromotionResult(
                            success=False,
                            new_status=script.status,
                            validation_result=None,
                            message=f"Failed to load script file: {e}"
                        )
                
                # Run AST validation
                validator = ASTSecurityValidator(allow_network=allow_network)
                validation_result = validator.validate(code)
                
                if not validation_result.is_safe:
                    # Build detailed error message
                    violations_summary = "\n".join([
                        f"  Line {v.line_number}: {v.message}"
                        for v in validation_result.violations[:5]  # Limit to first 5
                    ])
                    message = f"Security validation failed:\n{violations_summary}"
                    if len(validation_result.violations) > 5:
                        message += f"\n  ... and {len(validation_result.violations) - 5} more violations"
                    
                    return PromotionResult(
                        success=False,
                        new_status=script.status,
                        validation_result=validation_result,
                        message=message
                    )
            
            # Promotion successful - update status
            old_status = script.status
            script.status = target_status
            script.updated_at = datetime.utcnow()
            
            session.add(script)
            await session.commit()
            
            # Log to audit (if available)
            try:
                from client_app.app.services.enterprise_audit_service import enterprise_audit_service
                from automatia_shared.core.audit_models import RiskLevel
                
                await enterprise_audit_service.log_event(
                    action_type="PROMOTE_SCRIPT",
                    module="custom_script_service",
                    source_description=f"Script: {script.name} (ID: {script.id})",
                    risk_level=RiskLevel.MEDIUM.value,
                    additional_context={
                        "script_id": script.id,
                        "old_status": old_status,
                        "new_status": target_status,
                        "code_hash": script.code_hash
                    }
                )
            except Exception as audit_err:
                logger.warning(f"Failed to log promotion audit: {audit_err}")
            
            # PROMPT 8: Sync Promotion with Script Library
            try:
                from client_app.app.services.script_library_service import script_library_service
                await script_library_service.promote_script_from_source(
                    source_module='custom',
                    source_id=script.id,
                    target_status=target_status,
                    allow_network=allow_network
                )
                
                # PROMPT 4: Atomic Seal on Publish
                if target_status == 'published' and self.finishing_service:
                    from client_app.app.database.models import ScriptLibrary
                    # Find library script
                    async with AsyncSession(client_engine) as seal_session:
                        lib_script = (await seal_session.execute(
                            select(ScriptLibrary).where(
                                ScriptLibrary.source_module == 'custom',
                                ScriptLibrary.source_automation_id == script.id
                            )
                        )).scalar_one_or_none()
                        
                        if lib_script:
                             from client_app.app.services.asset_finishing_service import AssetFinishingService
                             finishing_svc = AssetFinishingService(session=seal_session)
                             await finishing_svc.seal_resource(
                                 script_id=lib_script.id,
                                 target_status='published'
                             )
                             logger.info(f"Auto-sealed library script {lib_script.id} on promotion")

            except Exception as e:
                print(f"[CustomScriptService] Warning: Failed to sync promotion/seal to library: {e}")

            return PromotionResult(
                success=True,
                new_status=target_status,
                validation_result=None,
                message=f"Script promoted from '{old_status}' to '{target_status}'"
            )

# Singleton Instance
custom_script_service = CustomScriptService()
