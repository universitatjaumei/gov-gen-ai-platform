
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import io
import os
import uuid

# Set non-interactive backend to prevent GUI windows popping up on server side logic
matplotlib.use('Agg')

class SafetySandbox:
    """
    Executes generated Python scripts in a semi-isolated environment.
    Visualizations are captured from matplotlib.
    """

    async def execute_script(self, script_code: str, df: pd.DataFrame) -> bytes:
        """
        Executes the provided script with 'df' in local scope.
        Expects the script to save a plot to 'plot_output.png' or just use plt.
        We intercept the plot generation.
        
        Args:
            script_code: Python code string.
            df: Dataframe to analyze.
            
        Returns:
            bytes: PNG image data.
            
        Raises:
            Exception: If execution fails.
        """
        import asyncio
        
        # Prepare execution scope
        local_scope = {'df': df, 'pd': pd, 'plt': plt}
        
        # Create a temp filename for this execution to avoid collisions
        temp_filename = f"plot_{uuid.uuid4()}.png"
        
        # Patch the script to use our temp filename if they hardcoded 'plot_output.png'
        script_code = script_code.replace('plot_output.png', temp_filename)
        
        def _run_sync():
            try:
                # Clear any existing plots
                plt.clf()
                
                # Execute
                exec(script_code, {}, local_scope)
                
                # Check if file was created
                if os.path.exists(temp_filename):
                    with open(temp_filename, 'rb') as f:
                        img_bytes = f.read()
                    os.remove(temp_filename)
                    return img_bytes
                else:
                    # If they didn't save but plotted, we save current figure
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    return buf.read()
            finally:
                plt.close('all')
                if os.path.exists(temp_filename):
                    try:
                        os.remove(temp_filename)
                    except:
                        pass

        try:
            return await asyncio.to_thread(_run_sync)
        except Exception as e:
            raise e
