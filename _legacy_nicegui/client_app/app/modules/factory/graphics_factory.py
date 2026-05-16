
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from client_app.app.services.script_generator_service import ScriptGeneratorService
from client_app.app.services.script_library_service import script_library_service # Unified Promotion
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

from client_app.app.modules.factory.analysis_prompt_builder import AnalysisPromptBuilder

# Constants for escalation
MAX_REFINEMENT_ITERATIONS = 3

@dataclass
class GraphicsScript:
    code: str
    metadata: Dict[str, Any]
    iteration_count: int = 0  # Track refinement iterations

class GraphicsFactory:
    def __init__(self, script_generator: ScriptGeneratorService = None, anonymizer: Optional[AnonymizationContext] = None):
        self.script_generator = script_generator or ScriptGeneratorService()
        self.anonymizer = anonymizer
        self.prompt_builder = AnalysisPromptBuilder()

    def analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extracts metadata from a DataFrame to assist AI generation.
        Anonymizes sample data if anonymizer is configured.
        """
        # Create a sample safely
        try:
            sample_df = df.head(5).copy()
        except Exception:
            sample_df = df.copy() # Fallback
        
        if self.anonymizer:
            try:
                # Select object/string columns that might contain PII
                cols = sample_df.select_dtypes(include=['object', 'string']).columns
                for col in cols:
                    # Apply anonymization function to verify string conversion and masking
                    # Use .loc to ensure assignment works on the dataframe copy
                    # Wrap in lambda to avoid issues if anonymizer is a proxy/mock (pandas introspection)
                    sample_df.loc[:, col] = sample_df[col].astype(str).apply(lambda x: self.anonymizer.anonymize(x))
            except Exception:
                # If anonymization fails, we continue with potentially unmasked data 
                pass

        # Generate summary stats
        try:
            # try include='all' to get categorical stats
            summary = df.describe(include='all').to_dict()
        except Exception:
            # Fallback for errors like 'ValueError: No objects to concatenate' 
            # which happens if mix of types fails or empty columns
            try:
                summary = df.describe().to_dict()
            except Exception:
                summary = {}

        return {
            "rows": len(df),
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "sample": sample_df.to_dict(orient='records'),
            "summary": summary
        }


    async def generate_business_questions(self, df_metadata: Dict[str, Any]) -> List[str]:
        """
        Generates a list of suggested business questions based on the dataframe metadata.
        """
        prompt = self.prompt_builder.build_business_questions_prompt(df_metadata)
        response = await self.script_generator.generate_custom_script(
            prompt=prompt,
            output_schema={} # Expecting JSON in response text/parsed
        )
        
        if not response.get('success'):
            return []

        # Extract 'questions' from JSON
        parsed = response.get('parsed', {})
        if parsed and 'questions' in parsed:
            return parsed['questions']
        
        # Fallback if parsed fails but content is present (simple manual parse)
        # Note: script_generator's extract_json should handle this mostly
        return ["Could not generate specific questions."]

    async def generate_visualization_suggestions(self, df_metadata: Dict[str, Any], question: str) -> List[Dict[str, Any]]:
        """
        Generates visualization suggestions for a given question.
        Returns list of dicts with type, reason, description.
        """
        prompt = self.prompt_builder.build_visualization_suggestions_prompt(df_metadata, question)
        response = await self.script_generator.generate_custom_script(
            prompt=prompt,
            output_schema={}
        )
        
        if not response.get('success'):
            return []
            
        parsed = response.get('parsed', {})
        if parsed and 'suggestions' in parsed:
            return parsed['suggestions']
            
        return []

    async def generate_script(self, df_metadata: Dict[str, Any], user_prompt: str) -> GraphicsScript:
        """
        Requests the AI Brain to generate a visualization script based on metadata and user prompt.
        """
        
        # Construct a rich context prompt
        system_context = f"""
        You are an expert Data Visualization assistant using Python (matplotlib, seaborn).
        
        DATA CONTEXT:
        - Columns: {df_metadata.get('columns')}
        - Types: {df_metadata.get('dtypes')}
        - Sample Data: {df_metadata.get('sample')}
        - Row Count: {df_metadata.get('rows')}
        
        TASK:
        Generate a COMPLETE, EXECUTABLE Python script to visualize this data based on the user's request.
        
        RULES:
        1. Assume the dataframe is loaded in a variable named `df`. DO NOT create dummy data.
        2. Use `matplotlib.pyplot` or `seaborn`.
        3. Do NOT use `plt.show()`. Instead, save the plot to 'plot_output.png'.
        4. Handle potential NaNs or type mismatches gracefully if possible.
        5. Return ONLY the python code, no markdown backticks.
        """
        
        full_prompt = f"{system_context}\n\nUSER REQUEST: {user_prompt}"
        
        # Call AI Brain via ScriptGeneratorService
        response = await self.script_generator.generate_custom_script(
            prompt=full_prompt,
            output_schema={} # We handle raw output or json extraction
        )
        
        if not response.get('success'):
            raise RuntimeError(f"Failed to generate script: {response.get('error')}")

        code = response.get('content', '')
        # If the API returns JSON with a 'code' field (depends on prompt/server), extract it.
        # But our plain prompt asks for just code. 
        # Ideally, we should enforce JSON in the prompt or robustly extract code block.
        # generate_custom_script tries to parse JSON in 'parsed'.
        
        if response.get('parsed') and 'code' in response['parsed']:
             code = response['parsed']['code']
        else:
             # Fallback extraction of code block if raw text
             parsed = self.script_generator._extract_json(code) # reusing helper if available or logic
             if parsed and 'code' in parsed:
                 code = parsed['code']
        
        # Cleanup markdown backticks if still present
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
            
        # Rehydrate code if anonymization was used
        if self.anonymizer:
            code = self.anonymizer.deanonymize(code)

        # PROMPT 8: Add to Script Library
        try:
            from datetime import datetime
            await script_library_service.add_script(
                source_module='graphics',
                name=f"Visualization Script {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                code=code,
                description=f"Auto-generated visualization",
                tags=['graphics', 'visualization'],
                user_prompt=user_prompt,
                source_metadata={'rows': df_metadata.get('rows'), 'columns': df_metadata.get('columns')}
            )
        except Exception as e:
             print(f"[GraphicsFactory] Warning: Failed to save script to library: {e}")

        return GraphicsScript(code=code, metadata=df_metadata, iteration_count=0)

    async def refine_script_with_escalation(
        self,
        script: GraphicsScript,
        feedback: str,
        execution_error: Optional[str] = None,
    ) -> Tuple[GraphicsScript, bool]:
        """
        Refines the script based on feedback with automatic escalation.

        Args:
            script: Current GraphicsScript to refine
            feedback: User feedback describing what needs to change
            execution_error: Optional error message from execution

        Returns:
            Tuple of (refined_script, needs_escalation)
            - needs_escalation is True if max iterations reached
        """
        # Check if we need to escalate
        if script.iteration_count >= MAX_REFINEMENT_ITERATIONS:
            return script, True  # Signal escalation needed

        # Build refinement prompt
        refinement_prompt = f"""
        CURRENT CODE:
        ```python
        {script.code}
        ```

        USER FEEDBACK:
        {feedback}

        {"EXECUTION ERROR:" + chr(10) + execution_error if execution_error else ""}

        DATA CONTEXT:
        - Columns: {script.metadata.get('columns')}
        - Row Count: {script.metadata.get('rows')}

        TASK:
        Modify the code to address the feedback. Return ONLY the corrected Python code.
        """

        # Anonymize prompt if anonymizer is configured
        prompt_to_send = refinement_prompt
        if self.anonymizer:
            prompt_to_send = self.anonymizer.anonymize(refinement_prompt)

        # Call AI for refinement
        response = await self.script_generator.generate_custom_script(
            prompt=prompt_to_send,
            output_schema={}
        )

        if not response.get('success'):
            # Refinement failed, return original with incremented count
            return GraphicsScript(
                code=script.code,
                metadata=script.metadata,
                iteration_count=script.iteration_count + 1
            ), False

        # Extract refined code
        refined_code = response.get('content', '')
        if response.get('parsed') and 'code' in response['parsed']:
            refined_code = response['parsed']['code']

        # Clean up markdown
        refined_code = refined_code.strip()
        if refined_code.startswith("```python"):
            refined_code = refined_code[9:]
        if refined_code.startswith("```"):
            refined_code = refined_code[3:]
        if refined_code.endswith("```"):
            refined_code = refined_code[:-3]
        refined_code = refined_code.strip()

        # Rehydrate if anonymization was used
        if self.anonymizer:
            refined_code = self.anonymizer.deanonymize(refined_code)

        return GraphicsScript(
            code=refined_code,
            metadata=script.metadata,
            iteration_count=script.iteration_count + 1
        ), False

    async def execute_script(self, script: GraphicsScript, df: pd.DataFrame) -> bytes:
        """
        Executes the generated script securely and returns the image bytes.
        Uses the unified SandboxExecutionService for consistency.
        """
        from client_app.app.services.sandbox_service import sandbox_service
        from automatia_shared.core.execution_manager import ExecutionPathManager
        import uuid
        import tempfile
        import os

        execution_id = str(uuid.uuid4())

        # Save DataFrame to temp file for sandbox execution
        temp_dir = tempfile.mkdtemp()
        df_path = os.path.join(temp_dir, "input_data.csv")
        df.to_csv(df_path, index=False)

        # Wrap the visualization code to save output
        wrapped_code = f'''
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

def extraer_datos(input_files):
    """Wrapper function for sandbox execution."""
    df = pd.read_csv(input_files[0]) if input_files else pd.DataFrame()

    # User's visualization code
{chr(10).join("    " + line for line in script.code.split(chr(10)))}

    # Save plot if not already saved
    import os
    output_path = 'plot_output.png'
    if not os.path.exists(output_path):
        plt.savefig(output_path, dpi=150, bbox_inches='tight')

    # Return the image bytes
    with open(output_path, 'rb') as f:
        return {{"image_bytes": f.read(), "success": True}}
'''

        result = await sandbox_service.execute_in_sandbox(
            code=wrapped_code,
            file_paths=[df_path],
            execution_id=execution_id,
            target_function="extraer_datos"
        )

        # Cleanup temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        if result.get('success') and result.get('data', {}).get('image_bytes'):
            return result['data']['image_bytes']
        elif result.get('error'):
            raise RuntimeError(f"Sandbox execution failed: {result['error']}")
        else:
            raise RuntimeError("No image output generated")
