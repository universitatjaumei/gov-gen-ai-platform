"""
ETL Service - Orchestrator for AI-powered data transformations.
ETL-03 implementation.

This service coordinates the complete ETL pipeline:
1. Read source file
2. Generate transformation script via ETLScriptFactory
3. Validate script via SecurityAuditor
4. Execute in sandbox
5. Write output
6. Persist job history
"""

from typing import Union, Dict, Any, Optional, List, Literal
import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime
import time

logger = logging.getLogger(__name__)


from typing import Any
from sqlmodel.ext.asyncio.session import AsyncSession
from automatia_shared.core.security import validate_code_ast, SecurityException

from client_app.app.modules.factory.etl_factory import ETLScriptFactory
from client_app.app.services.sandbox_service import SandboxExecutionService
from client_app.app.database.models import ETLJobHistory
from client_app.app.modules.privacy.anonymizer import AnonymizationContext


# --- BRAIN CLIENT (Centralizado) ---


class ETLService:
    """
    Orchestrates AI-powered ETL transformations.

    Coordinates script generation, validation, execution, and persistence.
    All AI code generation is done through BrainAPIClient (server API calls).
    """

    def __init__(
        self,
        session: AsyncSession,
        factory: Optional[ETLScriptFactory] = None,
        sandbox: Optional[SandboxExecutionService] = None,
        _test_brain_client: Optional[Any] = None
    ):
        """
        Inicializa el servicio ETL.

        Args:
            session: Sesión de base de datos para persistencia de historial.
            factory: Factoría encargada de construir los prompts y scripts ETL.
            sandbox: Servicio de ejecución segura en sandbox.
            _test_brain_client: Solo para tests - mock del cliente Brain con método generate_code.
        """
        self.session = session
        self._test_brain_client = _test_brain_client
        self.factory = factory or ETLScriptFactory()
        self.sandbox = sandbox

    async def _get_active_license_key(self) -> Optional[str]:
        """Retrieves active license key from local db."""
        from client_app.app.database.models import ServerConnection
        from client_app.app.database.db import client_engine
        from sqlmodel import select
        
        async with AsyncSession(client_engine) as session:
            stmt = select(ServerConnection).where(ServerConnection.is_active == True)
            res = await session.exec(stmt)
            conn = res.first()
            return conn.license_key if conn else None

    async def _get_brain_client(self):
        """
        Resuelve y retorna el cliente BrainAPIClient junto con la clave de licencia activa.

        La generación de código se hace siempre a través de la API del servidor.
        """
        # Solo para tests: usar mock inyectado si tiene el método generate_code
        if self._test_brain_client and hasattr(self._test_brain_client, 'generate_code'):
            logger.debug(f"[ETL Service] Using test brain client: {type(self._test_brain_client)}")
            return self._test_brain_client, "TEST_LICENSE_KEY"

        from client_app.app.clients.brain_client import BrainAPIClient
        from client_app.app.database.models import ServerConnection
        from client_app.app.database.db import client_engine
        
        # 1. Resolve License Key
        key = await self._get_active_license_key()
        
        # [FIX] Handle Seed Mismatch
        if not key or key in ["demo_key_123", "dev_key"]:
            key = "DEV_LICENSE_KEY_12345"

        # 2. Resolve URL from DB
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            return BrainAPIClient(base_url=url), key

    
    
    async def run_etl_pipeline(
        self,
        execution_id: str,
        source_file: str,
        output_file: str,
        output_format: str,
        transformation_mode: Literal['assisted', 'ai'] = 'ai',
        # For assisted mode (deterministic):
        operations: Optional[List[Any]] = None,
        # For AI mode:
        target_spec: Optional[Union[pd.DataFrame, dict, str]] = None,
        user_instructions: str = "",
        is_correction: bool = False,
        # Common:
        anonymization_config: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de ETL con soporte para dos modos:
        - 'assisted': Transformaciones deterministas sin IA
        - 'ai': Transformaciones complejas con scripts generados por IA

        Args:
            execution_id: Identificador único de la ejecución.
            source_file: Ruta al archivo de origen de datos.
            output_file: Ruta donde se guardará el resultado.
            output_format: Formato de salida (csv, excel, json, etc.).
            transformation_mode: 'assisted' para transformaciones deterministas, 'ai' para IA.
            operations: Lista de operaciones deterministas (requerido si mode='assisted').
            target_spec: Especificación del objetivo para IA (requerido si mode='ai').
            user_instructions: Instrucciones adicionales del usuario para la IA.
            is_correction: Si es True, utiliza modelos de mayor capacidad para supervisión.
            anonymization_config: Configuración de anonimización de PII.

        Returns:
            Diccionario con el estado, el script generado (si aplica), los datos transformados y metadatos.
        """

        start_time = time.time()
        
        try:
            # 1. Detect source format and read file
            source_format = self._detect_format(source_file)
            source_df = await self._read_source_file(source_file, source_format)
            
            # 2. Transform data based on mode
            if transformation_mode == 'assisted':
                # Deterministic mode - no AI required
                if not operations:
                    raise ValueError("Operations list is required for assisted mode")
                
                from client_app.app.services.deterministic_etl_service import DeterministicETLService
                deterministic_service = DeterministicETLService()
                
                transformed_df = await deterministic_service.execute_transformation(
                    source_df, operations
                )
                
                # Metadata for deterministic mode
                metadata = {
                    'mode': 'assisted',
                    'operations_count': len(operations),
                    'source_columns': list(source_df.columns),
                    'target_columns': list(transformed_df.columns)
                }
                # Generar script para persistencia y futura ejecución en flujos
                script_code = deterministic_service.generate_script(operations)
                
            else:
                # AI mode - generate and execute script
                # Relax requirement if user_instructions are provided
                actual_target_spec = target_spec
                if not actual_target_spec:
                    if not user_instructions:
                        raise ValueError("target_spec or user_instructions is required for AI mode")
                    # Fallback to a string spec derived from instructions if none provided
                    actual_target_spec = "Generar transformación basada en instrucciones adjuntas."
                
                client, license_key = await self._get_brain_client()
                logger.info(f"[ETL Service] Got brain client: {type(client)}, license_key: {license_key[:10]}...")

                # Crear contexto de anonimización para proteger datos personales
                # antes de enviarlos a la IA (mismo patrón que graphics_factory)
                anonymization_ctx = AnonymizationContext()

                logger.info(f"[ETL Service] Calling factory.generate_transformation_script with client={type(client)}")
                script_result = await self.factory.generate_transformation_script(
                    source_sample=source_df.head(10),  # Use sample for script generation
                    target_spec=actual_target_spec,
                    output_format=output_format,
                    user_instructions=user_instructions,
                    is_correction=is_correction,
                    ctx=anonymization_ctx,  # Anonimizar datos antes de enviar a IA
                    client=client,
                    license_key=license_key
                )
                
                script_code = script_result['script']
                metadata = script_result['metadata']
                metadata['mode'] = 'ai'
                
                # 3. Validate script security
                try:
                    validate_code_ast(script_code)
                except SecurityException as e:
                    raise SecurityException(f"Script validation failed: {str(e)}")
                
                # 4. Execute script in sandbox
                if self.sandbox:
                    # Use sandbox for secure execution
                    transformed_df = await self.sandbox.execute_in_sandbox(
                        code=script_code,
                        file_paths=[source_file],
                        execution_id=execution_id,
                        target_function="transform"
                    )
                else:
                    # Direct execution (for testing)
                    transformed_df = self._execute_script_direct(script_code, source_df)

                
            # 4.5. OPTIONAL: Apply Anonymization
            privacy_stats = None
            if anonymization_config:
                 anon_ctx = AnonymizationContext()
                 transformed_df = anon_ctx.anonymize_dataframe(transformed_df, anonymization_config)
                 privacy_stats = anon_ctx.get_stats()
            
            # 5. Write output
            await self._write_output(transformed_df, output_file, output_format)
            
            # 6. Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 7. Save job history
            await self._save_job_history(
                execution_id=execution_id,
                source_file=source_file,
                target_file=output_file,
                source_format=source_format,
                target_format=output_format,
                script_code=script_code,
                status='success',
                transformation_mode=transformation_mode,
                metadata=metadata,
                execution_time_ms=execution_time_ms,
                privacy_stats=privacy_stats
            )
            
            return {
                'status': 'success',
                'script': script_code,
                'data': transformed_df,
                'metadata': {**metadata, 'privacy_stats': privacy_stats}
            }
            
        except Exception as e:
            # Calculate execution time even on failure
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Save failure to history
            await self._save_job_history(
                execution_id=execution_id,
                source_file=source_file,
                target_file=output_file if 'output_file' in locals() else "",
                source_format=source_format if 'source_format' in locals() else "unknown",
                target_format=output_format if 'output_format' in locals() else "unknown",
                script_code=script_code if 'script_code' in locals() else None,
                status='failed',
                transformation_mode=transformation_mode,
                metadata={},
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _detect_format(self, file_path: str) -> str:
        """
        Detect file format from extension.
        
        Args:
            file_path: Path to file
        
        Returns:
            Format string: 'csv', 'excel', 'json', 'xml', 'parquet'
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        
        format_map = {
            '.csv': 'csv',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.json': 'json',
            '.xml': 'xml',
            '.parquet': 'parquet'
        }
        
        return format_map.get(ext, 'csv')
    
    async def _read_source_file(self, file_path: str, format: str) -> pd.DataFrame:
        """
        Read source file into DataFrame.
        
        Args:
            file_path: Path to source file
            format: File format
        
        Returns:
            DataFrame with source data
        """
        if format == 'csv':
            return pd.read_csv(file_path)
        elif format == 'excel':
            return pd.read_excel(file_path)
        elif format == 'json':
            return pd.read_json(file_path)
        elif format == 'xml':
            return pd.read_xml(file_path)
        elif format == 'parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _write_output(self, df: pd.DataFrame, file_path: str, format: str) -> None:
        """
        Write DataFrame to output file.
        
        Args:
            df: DataFrame to write
            file_path: Output file path
            format: Output format
        """
        if format == 'csv':
            df.to_csv(file_path, index=False)
        elif format == 'excel':
            df.to_excel(file_path, index=False)
        elif format == 'json':
            df.to_json(file_path, orient='records', indent=2)
        elif format == 'xml':
            df.to_xml(file_path, index=False)
        elif format == 'parquet':
            df.to_parquet(file_path, index=False)
        elif format == 'odt':
            from client_app.app.modules.factory.report_factory import ReportFactory
            factory = ReportFactory()
            context = {
                'title': f'Exportación: {Path(file_path).stem}',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'table_data': df,
                'summary': f"Datos exportados: {len(df)} filas."
            }
            factory.generate_odt(context, file_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _execute_script_direct(self, script_code: str, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Ejecuta el script de transformación directamente en el proceso actual.
        IMPORTANTE: Solo para propósitos de test o entornos controlados sin sandbox.
        """
        # Create execution namespace
        namespace = {
            'pd': pd,
            'df': source_df
        }
        
        # Execute script
        exec(script_code, namespace)
        
        # Call transform function
        transform_func = namespace.get('transform')
        if not transform_func:
            raise ValueError("Script must define a 'transform' function")
        
        return transform_func(source_df)
    
    async def _save_job_history(
        self,
        execution_id: str,
        source_file: str,
        target_file: str,
        source_format: str,
        target_format: str,
        script_code: str,
        status: str,
        transformation_mode: str,
        metadata: Dict[str, Any],
        execution_time_ms: int,
        error_message: Optional[str] = None,
        privacy_stats: Optional[Dict[str, int]] = None
    ) -> None:
        """
        Persiste el resultado de la ejecución del Job ETL en la base de datos de historial.
        """
        job = ETLJobHistory(
            execution_id=execution_id,
            source_file=source_file,
            target_file=target_file,
            source_format=source_format,
            target_format=target_format,
            script_content=script_code,
            transformation_mode=transformation_mode,
            status=status,
            error_message=error_message,
            execution_metadata=json.dumps(metadata),
            created_at=datetime.utcnow(),
            execution_time_ms=execution_time_ms,
            privacy_stats=privacy_stats
        )
        
        self.session.add(job)
        await self.session.commit()
