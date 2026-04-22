from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import hashlib
import logging

from client_app.app.services.external_script_audit_service import (
    external_script_audit_service,
    AuditResult
)
from client_app.app.services.script_adaptation_service import script_adaptation_service
from client_app.app.services.custom_script_service import custom_script_service

logger = logging.getLogger(__name__)

@dataclass
class IngestionResult:
    """Representa el resultado de la ingesta de un script externo."""
    success: bool  # Indica si el proceso técnico tuvo éxito
    script_id: Optional[int]  # ID del script creado en la base de datos
    status: str  # Estado post-ingesta: "registered", "pending_review", "rejected"
    audit_result: AuditResult  # Detalle del informe de seguridad
    adaptation_applied: bool  # Indica si se aplicó refactorización automática
    message: str  # Mensaje descriptivo del resultado

class ScriptIngestionService:
    """
    Servicio encargado de la importación segura de scripts Python externos.
    Coordina la auditoría de seguridad, la adaptación opcional al formato de la
    plataforma y el registro final en la biblioteca de scripts.
    """

    async def ingest_external_script(
        self,
        filename: str,
        code: str,
        description: str = None,
        auto_adapt: bool = False,
        target_type: str = "etl_transform"
    ) -> IngestionResult:
        """
        Procesa e integra un script Python externo en el sistema local.

        Args:
            filename: Nombre del archivo de origen.
            code: Contenido del código fuente.
            description: Descripción funcional opcional.
            auto_adapt: Si es True, intenta refactorizar el código para cumplir con contratos.
            target_type: Tipo de contrato al que se desea adaptar (ETL, Extracción, etc.).

        Returns:
            Objeto IngestionResult con el estado y los hallazgos de seguridad.
        """
        # 1. Auditar
        audit = external_script_audit_service.audit_script(code)

        if not audit.can_proceed_with_review:
            return IngestionResult(
                success=False,
                script_id=None,
                status="rejected",
                audit_result=audit,
                adaptation_applied=False,
                message=f"Script rechazado por seguridad: {audit.summary}"
            )

        # 2. Adaptar si se solicita
        final_code = code
        adaptation_applied = False

        if auto_adapt:
            adaptation = await script_adaptation_service.adapt_to_platform(
                code, target_type
            )
            if adaptation.success:
                final_code = adaptation.adapted_code
                adaptation_applied = True

        # 3. Calcular hash
        code_hash = hashlib.sha256(final_code.encode()).hexdigest()

        # 4. Registrar como DRAFT
        # Usamos kwargs que coincidan con CustomScript model
        script_data = {
            "name": Path(filename).stem,
            "description": description or f"Script importado: {filename}",
            "code": final_code,
            "code_hash": code_hash,
            "status": "DRAFT",
            "requires_review": len(audit.findings) > 0
        }

        try:
            script = await custom_script_service.create_script(**script_data)
            script_id = script.id
        except Exception as e:
            logger.error(f"Error registering script: {e}")
            return IngestionResult(
                success=False,
                script_id=None,
                status="error",
                audit_result=audit,
                adaptation_applied=adaptation_applied,
                message=f"Error al guardar script: {str(e)}"
            )

        # 5. Determinar estado
        status = "pending_review" if audit.findings else "registered"

        return IngestionResult(
            success=True,
            script_id=script_id,
            status=status,
            audit_result=audit,
            adaptation_applied=adaptation_applied,
            message=f"Script registrado como DRAFT (ID: {script_id})"
        )

script_ingestion_service = ScriptIngestionService()
