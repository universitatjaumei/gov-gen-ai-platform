"""
Script Library Service - Unified script management for all automation modules.
Prompt 8 Correction - Centralizes script promotion and validation.
Prompt 11 Integration - Auto-generates documentation on promotion.

Manages scripts from:
- Custom Scripts (ScriptGeneratorService)
- PDF Extraction (ExtractionService)
- ETL Transformation (ETLScriptFactory)
- Graphics (GraphicsFactory)
"""

from __future__ import annotations
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import hashlib
import logging

from automatia_shared.security.ast_validator import ASTSecurityValidator, ValidationResult

from client_app.app.database.db import client_engine
from client_app.app.database.models import ScriptLibrary
from client_app.app.services.doc_generator_service import doc_generator
from client_app.app.services.dev_crypto_service import dev_crypto_service
from client_app.app.core.state import state
from shared.automatia_shared.crypto_utils import rsa_signer
import json
import base64

logger = logging.getLogger(__name__)

# Storage paths (same as CustomScriptService)
STORAGE_ROOT = Path("data/storage/scripts")
SCRIPTS_DIR = STORAGE_ROOT / "src"
DOCS_DIR = STORAGE_ROOT / "docs"

SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ScriptAuditResult:
    """Resultado de auditoría de un script para promoción."""
    success: bool
    new_status: str
    message: str
    violations: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "new_status": self.new_status,
            "message": self.message,
            "violations": self.violations,
            "risk_score": self.risk_score
        }


class ScriptLibraryService:
    """
    Centralized service for managing scripts from all automation modules.
    Provides unified promotion workflow with AST validation.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def calculate_code_hash(self, code: str) -> str:
        """Calculate SHA256 hash of code."""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    async def add_script(
        self,
        source_module: str,
        name: str,
        code: str,
        description: str = "",
        tags: List[str] = None,
        ui_contract: Dict[str, Any] = None,
        data_contract: Dict[str, Any] = None,
        source_automation_id: Optional[int] = None,
        source_metadata: Dict[str, Any] = None,
        user_prompt: Optional[str] = None
    ) -> ScriptLibrary:
        """
        Add a script to the library.
        
        Args:
            source_module: Origin module ('custom', 'extraction', 'etl', 'graphics')
            name: Script name
            code: Python code
            description: Functional description
            tags: Search tags
            ui_contract: UI contract for execution
            data_contract: Data contract/schema
            source_automation_id: ID of source automation (if applicable)
            source_metadata: Module-specific metadata
            user_prompt: Original user prompt
            
        Returns:
            Created ScriptLibrary instance
        """
        # Sanitize name for filename
        sanitized_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        
        # Create initial record to get ID
        script = ScriptLibrary(
            source_module=source_module,
            name=name,
            description=description,
            tags=tags or [],
            script_path="",  # Will be set after flush
            doc_path="",
            code_hash=self.calculate_code_hash(code),
            ui_contract=ui_contract or {},
            data_contract=data_contract or {},
            source_automation_id=source_automation_id,
            source_metadata=source_metadata or {},
            user_prompt=user_prompt,
            status="draft"
        )
        
        async with AsyncSession(client_engine) as session:
            session.add(script)
            await session.flush()
            await session.refresh(script)
            
            # Save files with ID-based naming (prefixed to avoid collision with CustomScript)
            filename_py = f"lib_{script.id}_{sanitized_name}.py"
            filename_md = f"lib_{script.id}_{sanitized_name}.md"
            
            with open(SCRIPTS_DIR / filename_py, "w", encoding="utf-8") as f:
                f.write(code)
            
            doc_content = f"# {name}\n\n{description}\n"
            if user_prompt:
                doc_content += f"\n## Prompt Original\n{user_prompt}\n"
            
            with open(DOCS_DIR / filename_md, "w", encoding="utf-8") as f:
                f.write(doc_content)
            
            script.script_path = filename_py
            script.doc_path = filename_md
            
            session.add(script)
            await session.commit()
            await session.refresh(script)
            
            return script
    
    async def get_script(self, script_id: int) -> Optional[ScriptLibrary]:
        """Get script by ID, loading code from disk."""
        async with AsyncSession(client_engine) as session:
            script = await session.get(ScriptLibrary, script_id)
            if script and script.script_path:
                try:
                    file_path = SCRIPTS_DIR / script.script_path
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as f:
                            # Store code in transient attribute for access
                            script.code = f.read()
                except Exception as e:
                    script.code = f"# Error loading script: {e}"
            return script
    async def promote_script(
        self,
        script_id: int,
        target_status: str,
        allow_network: bool = False
    ) -> ScriptAuditResult:
        """
        Promote script to new status with AST validation.
        
        Args:
            script_id: Script ID
            target_status: Target status ('validated' or 'published')
            allow_network: Allow network imports in validation
            
        Returns:
            ScriptAuditResult
        """
        valid_transitions = {
            'draft': ['validated'],
            'validated': ['published', 'draft'],
            'published': ['draft']
        }
        
        async with AsyncSession(client_engine) as session:
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                return ScriptAuditResult(
                    success=False,
                    new_status="unknown",
                    message=f"Script {script_id} not found"
                )
            
            # Check valid transition
            if target_status not in valid_transitions.get(script.status, []):
                return ScriptAuditResult(
                    success=False,
                    new_status=script.status,
                    message=f"Invalid transition from '{script.status}' to '{target_status}'"
                )
            
            # Validate security if promoting
            if target_status in ['validated', 'published']:
                # Load code from disk
                try:
                    with open(SCRIPTS_DIR / script.script_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                except Exception as e:
                    return ScriptAuditResult(
                        success=False,
                        new_status=script.status,
                        message=f"Failed to load script file: {e}"
                    )
                
                # Run AST validation
                validator = ASTSecurityValidator(allow_network=allow_network)
                validation_result = validator.validate(code)
                
                if not validation_result.is_safe:
                    violations_summary = "\n".join([
                        f"  Line {v.line_number}: {v.message}"
                        for v in validation_result.violations[:5]
                    ])
                    message = f"Security validation failed:\n{violations_summary}"
                    if len(validation_result.violations) > 5:
                        message += f"\n  ... and {len(validation_result.violations) - 5} more violations"
                    
                    # Store validation errors
                    script.validation_errors = message
                    session.add(script)
                    await session.commit()
                    
                    return ScriptAuditResult(
                        success=False,
                        new_status=script.status,
                        message=message,
                        violations=[
                            {
                                'type': v.violation_type,
                                'line': v.line_number,
                                'message': v.message,
                                'risk': v.risk_level.value
                            }
                            for v in validation_result.violations
                        ],
                        risk_score=len(validation_result.violations) * 10.0 # Simple risk scoring
                    )
            
            # Promotion successful
            old_status = script.status
            script.status = target_status
            script.updated_at = datetime.utcnow()
            script.validation_errors = None  # Clear errors on successful promotion

            # Contract Auto-Generation: Generate contracts from validated execution metadata
            if target_status in ['validated', 'published']:
                try:
                    from client_app.app.services.execution_session_service import execution_session_service
                    from client_app.app.services.data_contract_service import data_contract_service
                    
                    # Recuperar metadata de la última ejecución validada
                    execution_session = await execution_session_service.get_execution_session(script_id)
                    
                    if execution_session and execution_session.get('validated'):
                        # Generar Input Contract desde variables de entrada
                        input_metadata = execution_session.get('input_metadata', {})
                        if input_metadata.get('detected_fields'):
                            input_contract = await data_contract_service.generate_input_contract(
                                input_metadata=input_metadata
                            )
                            script.input_contract = input_contract
                            logger.info(f"Input contract generated for script {script_id}")
                        
                        # Generar Output Contract desde resultado
                        output_metadata = execution_session.get('output_metadata', {})
                        if output_metadata.get('fields'):
                            output_contract = await data_contract_service.generate_output_contract(
                                output_metadata=output_metadata
                            )
                            script.output_contract = output_contract
                            logger.info(f"Output contract generated for script {script_id}")
                    else:
                        logger.info(f"No validated execution session found for script {script_id}, skipping contract generation")
                        
                except Exception as e:
                    # Contract generation failure should not block promotion
                    logger.warning(f"Failed to generate contracts for script {script_id}: {e}")

            # Prompt 11: Auto-generate documentation on promotion
            if target_status in ['validated', 'published']:
                try:
                    doc_path = doc_generator.save_readme(
                        script=script,
                        base_path=DOCS_DIR,
                        code=code,
                        include_changelog=True
                    )
                    # Update doc_path if different from current
                    new_doc_filename = doc_path.name
                    if script.doc_path != new_doc_filename:
                        # Remove old doc if exists and different
                        if script.doc_path:
                            old_doc_path = DOCS_DIR / script.doc_path
                            if old_doc_path.exists() and old_doc_path != doc_path:
                                old_doc_path.unlink(missing_ok=True)
                        script.doc_path = new_doc_filename

                    logger.info(f"Documentation generated for script {script_id}: {doc_path}")
                except Exception as e:
                    # Documentation generation failure should not block promotion
                    logger.warning(f"Failed to generate documentation for script {script_id}: {e}")

            session.add(script)
            await session.commit()

            return ScriptAuditResult(
                success=True,
                new_status=target_status,
                message=f"Script promoted from '{old_status}' to '{target_status}'"
            )
    
    async def update_script_from_source(
        self,
        source_module: str,
        source_id: int,
        code: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ):
        """Update script library entry based on source ID."""
        if session:
            return await self._update_script_impl(session, source_module, source_id, code, description, name)
        
        async with AsyncSession(client_engine) as session:
            return await self._update_script_impl(session, source_module, source_id, code, description, name)

    async def _update_script_impl(
        self,
        session: AsyncSession,
        source_module: str,
        source_id: int,
        code: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None
    ):
        stmt = select(ScriptLibrary).where(
            ScriptLibrary.source_module == source_module,
            ScriptLibrary.source_automation_id == source_id
        )
        result = await session.execute(stmt)
        script = result.scalars().first()
            
        if not script:
            return False
            
        if name: script.name = name
        if description: script.description = description
        
        if code:
            script.code_hash = self.calculate_code_hash(code)
            # Update file
            if script.script_path:
                try:
                    with open(SCRIPTS_DIR / script.script_path, "w", encoding="utf-8") as f:
                        f.write(code)
                except Exception as e:
                    print(f"Error updating library file: {e}")
        
        if description and script.doc_path:
            try:
                with open(DOCS_DIR / script.doc_path, "w", encoding="utf-8") as f:
                    f.write(f"# {script.name}\n\n{description}\n")
            except Exception: pass
        
        script.updated_at = datetime.utcnow()
        session.add(script)
        await session.commit()
        return True

    async def search_scripts(
        self,
        source_module: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[ScriptLibrary]:
        """
        Search scripts in library.
        
        Args:
            source_module: Filter by module
            status: Filter by status
            tags: Filter by tags (any match)
            query: Text search in name/description
            
        Returns:
            List of matching scripts
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(ScriptLibrary)
            
            if source_module:
                stmt = stmt.where(ScriptLibrary.source_module == source_module)
            
            if status:
                stmt = stmt.where(ScriptLibrary.status == status)
            
            # Execute query
            result = await session.execute(stmt)
            scripts = result.scalars().all()
            
            # Filter by tags (in-memory, since JSON queries are complex)
            if tags:
                scripts = [s for s in scripts if any(tag in s.tags for tag in tags)]
            
            # Filter by text query
            if query:
                query_lower = query.lower()
                scripts = [
                    s for s in scripts
                    if query_lower in s.name.lower() or
                       (s.description and query_lower in s.description.lower())
                ]
            
            return scripts

    async def update_script_metadata(self, script_id: int, name: str, description: str):
        """Update basic metadata for a script library entry."""
        async with AsyncSession(client_engine) as session:
            script = await session.get(ScriptLibrary, script_id)
            if script:
                script.name = name
                script.description = description
                script.updated_at = datetime.utcnow()
                session.add(script)
                await session.commit()
                return True
            return False

    async def update_script_sample_data(self, script_id: int, data: Any, source: str = "auto") -> bool:
        """
        Guarda una muestra de datos en el campo source_metadata de ScriptLibrary 
        (útil para ETL y Graphics que se guardan como scripts).
        """
        import json
        from datetime import datetime
        try:
            from client_app.app.services.preview_data_service import preview_data_service
            
            # 1. Normalizar los datos
            preview_result = preview_data_service._normalize_output_to_preview(data, step_type=source, max_rows=10)
            
            # 2. Enriquecer metadata
            if not preview_result.metadata:
                preview_result.metadata = {}
            preview_result.metadata["generated_at"] = datetime.utcnow().isoformat()
            
            sample_json = {
                "columns": preview_result.columns,
                "rows": preview_result.rows,
                "preview_rows": preview_result.preview_rows,
                "row_count": preview_result.row_count,
                "metadata": preview_result.metadata,
                "source_type": source
            }
            
            # 3. Guardar en source_metadata
            async with AsyncSession(client_engine) as session:
                script = await session.get(ScriptLibrary, script_id)
                if not script:
                    return False
                    
                metadata = script.source_metadata or {}
                metadata['sample_data'] = json.dumps(sample_json)
                
                # Para SQLite/SQLAlchemy JSON columns update
                script.source_metadata = metadata.copy()
                script.updated_at = datetime.utcnow()
                
                session.add(script)
                await session.commit()
                return True
        except Exception as e:
            logger.warning(f"Error actualizando sample_data para script {script_id}: {e}")
            return False

    
    async def cleanup_stale_drafts(self, older_than_hours: int = 24) -> int:
        """
        Clean up draft scripts created more than X hours ago.
        This cleans up intermediate generations from factories.
        
        Args:
            older_than_hours: Threshold in hours
            
        Returns:
            Number of scripts deleted
        """
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(hours=older_than_hours)
        count = 0
        
        async with AsyncSession(client_engine) as session:
            # Find stale drafts
            stmt = select(ScriptLibrary).where(
                ScriptLibrary.status == "draft",
                ScriptLibrary.created_at < threshold
            )
            result = await session.execute(stmt)
            stale_scripts = result.scalars().all()
            
            for script in stale_scripts:
                # Delete files
                if script.script_path:
                    try: (SCRIPTS_DIR / script.script_path).unlink(missing_ok=True)
                    except: pass
                if script.doc_path:
                    try: (DOCS_DIR / script.doc_path).unlink(missing_ok=True)
                    except: pass
                
                await session.delete(script)
                count += 1
            
            await session.commit()
            
        return count


    async def get_atom_dependencies(self, script_id: int) -> Dict[str, Any]:
        """
        Check what flows and other resources depend on this atom.
        
        Args:
            script_id: ID of the script to check
            
        Returns:
            Dictionary with:
            {
                'flows': [{'id': 1, 'name': 'Flow Name', 'step_names': ['Step 1']}],
                'count': 1
            }
        """
        from client_app.app.database.models import FlowRegistry
        
        dependencies = {
            'flows': [],
            'count': 0
        }
        
        async with AsyncSession(client_engine) as session:
            # Get the script to check
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                return dependencies
            
            # Get all active flows
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            flows = result.scalars().all()
            
            # Check each flow for references to this script
            for flow in flows:
                try:
                    steps = json.loads(flow.steps) if flow.steps else []
                    matching_steps = []
                    
                    for step in steps:
                        # Check if step references this script by ID
                        if step.get('script_id') == str(script_id):
                            matching_steps.append(step.get('name', 'Unnamed Step'))
                        # Also check config for potential references
                        elif 'config' in step:
                            config = step['config']
                            # Check if config has script_id or automation_id references
                            if config.get('script_id') == str(script_id) or \
                               config.get('automation_id') == str(script_id):
                                matching_steps.append(step.get('name', 'Unnamed Step'))
                    
                    if matching_steps:
                        dependencies['flows'].append({
                            'id': flow.id,
                            'name': flow.name,
                            'step_names': matching_steps
                        })
                        dependencies['count'] += 1
                        
                except Exception as e:
                    logger.warning(f"Error checking flow {flow.id} for dependencies: {e}")
                    continue
        
        return dependencies

    async def delete_script(self, script_id: int, force: bool = False) -> bool:
        """
        Delete script from library and disk.
        
        Args:
            script_id: ID of the script to delete
            force: If True, delete even if there are dependencies
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If script has dependencies and force=False
        """
        # Check dependencies if not forcing
        if not force:
            deps = await self.get_atom_dependencies(script_id)
            if deps['count'] > 0:
                flow_names = [f"'{f['name']}" for f in deps['flows']]
                raise ValueError(
                    f"Cannot delete: This atom is used by {deps['count']} flow(s): "
                    f"{', '.join(flow_names)}. Use force=True to delete anyway."
                )
        
        async with AsyncSession(client_engine) as session:
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                return False
            
            # Delete files
            if script.script_path:
                try:
                    (SCRIPTS_DIR / script.script_path).unlink(missing_ok=True)
                except:
                    pass
            
            if script.doc_path:
                try:
                    (DOCS_DIR / script.doc_path).unlink(missing_ok=True)
                except:
                    pass
            
            # Delete manifest if exists
            manifest_path = SCRIPTS_DIR / f"{script.script_path}.signed.json"
            if manifest_path.exists():
                try:
                    manifest_path.unlink(missing_ok=True)
                except:
                    pass
            
            await session.delete(script)
            await session.commit()
            
            # Log audit event
            try:
                from client_app.app.services.enterprise_audit_service import enterprise_audit_service
                from automatia_shared.core.audit_models import RiskLevel
                await enterprise_audit_service.log_event(
                    action_type="DELETE_ATOM",
                    module="script_library_service",
                    source_description=f"Deleted atom: {script.name} (ID: {script_id})",
                    risk_level=RiskLevel.MEDIUM.value,
                    additional_context={
                        "script_id": script_id,
                        "forced": force
                    }
                )
            except Exception:
                pass
            
            return True


    async def seal_script(self, script_id: int) -> bool:
        """
        Sella un activo (script o playbook) con firma RSA local si el rol es Partner.
        """
        # 1. Validar Rol
        if state.current_role != "partner":
            raise PermissionError("Acceso denegado: Solo los Partners pueden sellar activos.")

        async with AsyncSession(client_engine) as session:
            # 2. Recuperar Script
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                return False

            # 3. Preparar Payload para firma
            payload = {
                "id": script.id,
                "source_module": script.source_module,
                "name": script.name,
                "code_hash": script.code_hash,
                "ui_contract": script.ui_contract,
                "data_contract": script.data_contract,
                "timestamp": datetime.utcnow().isoformat()
            }

            # 4. Canonicalizar JSON para firma determinista
            payload_json = json.dumps(payload, sort_keys=True)

            # 5. Firmar
            private_key = dev_crypto_service.get_private_key()
            if not private_key:
                raise ValueError("No se encontró la llave privada de desarrollo para firmar.")

            signature = rsa_signer.sign_payload(payload_json, private_key)

            # 6. Generar Manifiesto Firmado
            manifest = {
                "payload": payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
                "public_key": dev_crypto_service.get_public_key().decode('utf-8') if dev_crypto_service.get_public_key() else None
            }

            # 7. Guardar Manifiesto en el directorio del activo
            manifest_filename = "manifest.signed.json"
            # Asumimos que el manifiesto vive junto al script
            manifest_path = SCRIPTS_DIR / manifest_filename
            # Nota: Si hay múltiples scripts, esto sobreescribiría. 
            # Para esta implementación, lo guardamos en la raíz de scripts o especificamos uno por script id.
            # Mejor guardar uno por script para evitar colisiones:
            manifest_path = SCRIPTS_DIR / f"manifest_{script.id}.signed.json"
            # Pero el plan dice manifest.signed.json en el directorio del script.
            # Como script_path es un archivo, no un directorio, lo guardamos al lado:
            if script.script_path:
                manifest_path = SCRIPTS_DIR / f"{script.script_path}.signed.json"
            
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            # 8. Actualizar Estado
            script.status = "validated"
            script.updated_at = datetime.utcnow()
            session.add(script)
            
            # 9. Auditoría
            try:
                from client_app.app.services.enterprise_audit_service import enterprise_audit_service
                from automatia_shared.core.audit_models import RiskLevel
                await enterprise_audit_service.log_event(
                    action_type="SEAL_ASSET",
                    module="script_library_service",
                    source_description=f"Asset: {script.name} (ID: {script.id})",
                    risk_level=RiskLevel.MEDIUM.value,
                    additional_context={"script_id": script.id, "manifest_path": str(manifest_path)}
                )
            except Exception: pass

            await session.commit()
            return True


    async def verify_asset_seal(self, script_id: int) -> bool:
        """
        Verifica la integridad y el sello de un activo.
        
        Si no hay sello, se permite (warning en logs).
        Si hay sello, debe ser íntegro (mismo hash) y la firma debe ser válida.
        """
        async with AsyncSession(client_engine) as session:
            # 1. Recuperar Script
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                raise ValueError(f"Script {script_id} no encontrado.")

            # 2. Cargar código actual y calcular hash
            try:
                with open(SCRIPTS_DIR / script.script_path, "r", encoding="utf-8") as f:
                    current_code = f.read()
                current_hash = self.calculate_code_hash(current_code)
            except Exception as e:
                raise ValueError(f"No se pudo leer el archivo del script: {e}")

            # 3. Buscar Manifiesto
            manifest_path = SCRIPTS_DIR / f"{script.script_path}.signed.json"
            if not manifest_path.exists():
                logger.warning(f"Activo {script.id} ({script.name}) no está sellado. Ejecutando sin verificación de Partner.")
                return True

            # 4. Cargar Manifiesto
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                payload = manifest.get("payload", {})
                signature_b64 = manifest.get("signature")
                public_key_pem = manifest.get("public_key")
            except Exception as e:
                raise ValueError(f"Error al leer el manifiesto de seguridad: {e}")

            # 5. Verificar Integridad (Hash)
            if current_hash != payload.get("code_hash"):
                raise ValueError(f"Integridad violada: El código de '{script.name}' ha sido alterado después del sellado.")

            # 6. Verificar Firma
            if not signature_b64:
                raise ValueError("Manifiesto corrupto: Falta la firma digital.")

            try:
                signature = base64.b64decode(signature_b64)
                # Payload para verificar debe ser idéntico al que se firmó (canonicalizado)
                payload_json = json.dumps(payload, sort_keys=True)
                
                # Usar la llave pública del manifiesto o una configurada para el Partner
                # En desarrollo, usamos la que viene en el manifiesto.
                pub_key = public_key_pem.encode('utf-8') if public_key_pem else dev_crypto_service.get_public_key()
                
                is_valid = rsa_signer.verify_signature(payload_json, signature, pub_key)
                
                if not is_valid:
                    raise ValueError("Firma inválida: No se pudo verificar la autenticidad del Partner.")
                
            except Exception as e:
                if isinstance(e, ValueError): raise e
                raise ValueError(f"Error durante la verificación de seguridad: {e}")

            logger.info(f"Sello verificado con éxito para '{script.name}' (ID: {script.id})")
            return True

    async def toggle_favorite(self, script_id: int) -> bool:
        """Toggle favorite status for a script."""
        async with AsyncSession(client_engine) as session:
            script = await session.get(ScriptLibrary, script_id)
            if not script:
                return False
            
            new_status = not script.is_favorite
            script.is_favorite = new_status
            session.add(script)
            await session.commit()
            return new_status


# Singleton instance
script_library_service = ScriptLibraryService()
