"""
ETL Script Factory - AI-powered transformation script generation.
ETL-02 implementation.

This module generates Python scripts for data transformation using AI,
similar to how extraction_service generates extraction scripts.
"""

from typing import Any, Union, Dict, List, Optional, Tuple
import pandas as pd
import json
from pathlib import Path

from client_app.app.modules.privacy.anonymizer import AnonymizationContext
from client_app.app.services.script_library_service import script_library_service  # Unified Promotion

# Constants for escalation
MAX_REFINEMENT_ITERATIONS = 3


class ETLScriptFactory:
    """
    Generates Python transformation scripts using AI.

    All AI code generation is done through BrainAPIClient (server API calls).
    The client is passed via method parameters, not stored in the instance.
    """

    def __init__(self):
        """Initialize the factory. No state required - client is passed per call."""
        pass
    
    async def generate_transformation_script(
        self,
        source_sample: pd.DataFrame,
        target_spec: Union[pd.DataFrame, dict, str],
        output_format: str,
        user_instructions: str = "",
        is_correction: bool = False,
        ctx: Optional[AnonymizationContext] = None,
        client: Any = None,
        license_key: str = "TRIAL-KEY"
    ) -> dict:
        """
        Genera script Python basándose en muestra origen y especificación destino.
        
        Args:
            source_sample: DataFrame con muestra del archivo origen (primeras filas)
            target_spec: Especificación de salida deseada:
                - pd.DataFrame: Ejemplo de salida deseada
                - dict: Esquema JSON de salida
                - str: Descripción textual de transformaciones
            output_format: Formato destino (csv, excel, xml, json, parquet)
            user_instructions: Instrucciones adicionales del usuario
            is_correction: Si True, usa Tier 3 (Supervisión) para corregir script.
                          Si False, usa Tier 2 (Lógica) para generación inicial.
            client: BrainAPIClient para llamadas a la API del servidor (requerido).
            license_key: Clave de licencia para el cliente.
        
        Returns:
            {
                'script': str,  # Código Python generado
                'metadata': {
                    'model_used': str,
                    'tokens': int,
                    'source_columns': list,
                    'target_columns': list
                }
            }
        """
        # 1. Prepare context for AI (with optional anonymization)
        source_info = self._prepare_source_context(source_sample, ctx)
        target_info = self._prepare_target_context(target_spec, output_format, ctx)
        
        # 2. Build prompt
        prompt = self._build_transformation_prompt(
            source_info, 
            target_info, 
            output_format,
            user_instructions
        )
        
        # 3. Call AI Brain via API
        # Tier 2 (sys_etl_transform_generator) for initial generation
        # Tier 3 (sys_etl_transform_supervisor) for supervision/correction
        service_id = "sys_etl_transform_supervisor" if is_correction else "sys_etl_transform_generator"

        import logging
        logger = logging.getLogger(__name__)

        if not client:
            raise ValueError("BrainAPIClient is required for code generation")

        # Verify client has required method
        if not hasattr(client, 'generate_code'):
            raise ValueError(f"Client {type(client).__name__} does not have 'generate_code' method. Expected BrainAPIClient.")

        logger.debug(f"[ETL Factory] Using client: {type(client).__name__}")

        response = await client.generate_code(
            prompt=prompt,
            language="python",
            service_id=service_id,
            license_key=license_key
        )
        
        # 4. Extract and validate script
        script = self._extract_script_from_response(response)

        # Rehydrate script if anonymization was used
        if ctx:
            script = ctx.deanonymize(script)

        # PROMPT 8: Add to Script Library
        try:
            from datetime import datetime
            await script_library_service.add_script(
                source_module='etl',
                name=f"ETL Transformation {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                code=script,
                description=f"Auto-generated transformation for {output_format}",
                tags=['etl', 'transformation', output_format],
                user_prompt=user_instructions,
                source_metadata={
                    'source_columns': list(source_sample.columns),
                    'target_spec_type': type(target_spec).__name__
                }
            )
        except Exception as e:
            # Non-blocking error
            print(f"[ETLFactory] Warning: Failed to save script to library: {e}")
        
        # 5. Build metadata
        metadata = {
            'model_used': response.get('model', 'unknown'),
            'tokens': response.get('tokens', 0),
            'source_columns': list(source_sample.columns),
            'target_columns': self._extract_target_columns(target_spec)
        }
        
        return {
            'script': script,
            'metadata': metadata
        }
    
    def _prepare_source_context(self, df: pd.DataFrame, ctx: Optional[AnonymizationContext] = None) -> dict:
        """Prepara contexto del archivo origen."""
        sample_rows = df.head(3).to_dict(orient='records')
        
        # Apply anonymization if context is available
        if ctx:
            sample_rows = ctx.anonymize(sample_rows) if isinstance(sample_rows, (list, dict)) else sample_rows
            
        return {
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'sample_rows': sample_rows,
            'row_count': len(df)
        }
    
    def _prepare_target_context(self, target_spec: Union[pd.DataFrame, dict, str], output_format: str, ctx: Optional[AnonymizationContext] = None) -> dict:
        """Prepara contexto de salida deseada."""
        if isinstance(target_spec, pd.DataFrame):
            sample_rows = target_spec.head(3).to_dict(orient='records')
            if ctx:
                sample_rows = ctx.anonymize(sample_rows)
            return {
                'type': 'example',
                'columns': list(target_spec.columns),
                'sample_rows': sample_rows,
                'format': output_format
            }
        elif isinstance(target_spec, dict):
            return {
                'type': 'schema',
                'schema': target_spec,
                'format': output_format
            }
        else:  # str
            return {
                'type': 'description',
                'description': target_spec,
                'format': output_format
            }
    
    def _build_transformation_prompt(
        self, 
        source_info: dict, 
        target_info: dict,
        output_format: str,
        user_instructions: str
    ) -> str:
        """Construye prompt para la IA."""
        prompt = f"""# ETL Transformation Script Generator

## Source Data
Columns: {', '.join(source_info['columns'])}
Data types: {json.dumps(source_info['dtypes'], indent=2)}
Sample rows (first 3):
{json.dumps(source_info['sample_rows'], indent=2, ensure_ascii=False)}

## Target Specification
"""
        
        if target_info['type'] == 'example':
            prompt += f"""Type: Example DataFrame
Target columns: {', '.join(target_info['columns'])}
Sample output (first 3 rows):
{json.dumps(target_info['sample_rows'], indent=2, ensure_ascii=False)}
"""
        elif target_info['type'] == 'schema':
            prompt += f"""Type: JSON Schema
Schema: {json.dumps(target_info['schema'], indent=2, ensure_ascii=False)}
"""
        else:  # description
            prompt += f"""Type: Textual Description
Description: {target_info['description']}
"""
        
        prompt += f"""
## Output Format
{output_format}

## User Instructions
{user_instructions or 'None'}

## Task
Generate a Python function called `transform(df: pd.DataFrame) -> pd.DataFrame` that:
1. Takes the source DataFrame as input
2. Applies necessary transformations to match the target specification
3. Returns the transformed DataFrame
4. Includes error handling for common issues
5. Documents all transformations with inline comments

## Important Rules
- Use pandas operations (rename, drop, merge, apply, etc.)
- Handle missing values appropriately
- Preserve data types when possible
- Add a docstring explaining the transformation
- Do not include any import statements (they will be provided)
- Do not include any file I/O operations
- Return ONLY the transform function code

## Output
Provide ONLY the Python function code, no explanations:
```python
def transform(df: pd.DataFrame) -> pd.DataFrame:
    ...
```
"""
        return prompt
    
    def _extract_script_from_response(self, response: dict) -> str:
        """Extrae el código Python de la respuesta de la IA."""
        import re

        # Assume response structure: {'code': '...', 'model': '...', 'tokens': ...}
        code = response.get('code', '')

        # Clean up code blocks if wrapped in markdown
        if '```python' in code:
            # Extract code from markdown blocks
            match = re.search(r'```python\s*(.*?)\s*```', code, re.DOTALL)
            if match:
                code = match.group(1)
        elif '```' in code:
            match = re.search(r'```\s*(.*?)\s*```', code, re.DOTALL)
            if match:
                code = match.group(1)

        return code.strip()
    
    def _extract_target_columns(self, target_spec: Union[pd.DataFrame, dict, str]) -> List[str]:
        """Extrae lista de columnas objetivo."""
        if isinstance(target_spec, pd.DataFrame):
            return list(target_spec.columns)
        elif isinstance(target_spec, dict):
            return list(target_spec.keys())
        else:
            return []

    async def refine_transformation_script(
        self,
        original_script: str,
        execution_error: str,
        user_feedback: str,
        source_columns: List[str],
        ctx: Optional[AnonymizationContext] = None,
        client: Any = None,
        license_key: str = "TRIAL-KEY",
        iteration: int = 0,
    ) -> Tuple[str, bool]:
        """
        Refines an ETL transformation script based on errors and feedback.

        Args:
            original_script: The current script code to refine
            execution_error: Error message from script execution
            user_feedback: User's description of what needs to change
            source_columns: List of source data columns for context
            ctx: Optional AnonymizationContext for privacy
            client: BrainAPIClient for API calls
            license_key: License key for the client
            iteration: Current iteration count

        Returns:
            Tuple of (refined_script, needs_escalation)
            - needs_escalation is True if max iterations reached
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check if we need to escalate
        if iteration >= MAX_REFINEMENT_ITERATIONS:
            logger.info(f"[ETL Factory] Max iterations ({MAX_REFINEMENT_ITERATIONS}) reached, escalation needed")
            return original_script, True

        if not client:
            raise ValueError("BrainAPIClient is required for script refinement")

        # Build refinement prompt
        refinement_prompt = f"""# ETL Script Refinement

## Current Script
```python
{original_script}
```

## Execution Error
{execution_error}

## User Feedback
{user_feedback}

## Source Data Columns
{', '.join(source_columns)}

## Task
Correct the transformation script to address the error and feedback.
Return ONLY the corrected Python function code.

## Output Format
```python
def transform(df: pd.DataFrame) -> pd.DataFrame:
    ...
```
"""

        # Anonymize prompt if context is available
        prompt_to_send = refinement_prompt
        if ctx:
            prompt_to_send = ctx.anonymize(refinement_prompt)

        # Call AI for refinement (use supervision tier for corrections)
        response = await client.generate_code(
            prompt=prompt_to_send,
            language="python",
            service_id="sys_etl_transform_supervisor",
            license_key=license_key
        )

        # Extract refined script
        refined_script = self._extract_script_from_response(response)

        # Rehydrate if anonymization was used
        if ctx:
            refined_script = ctx.deanonymize(refined_script)

        return refined_script, False
