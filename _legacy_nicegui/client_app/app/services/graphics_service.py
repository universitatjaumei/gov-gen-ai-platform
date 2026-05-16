
import pandas as pd
from typing import Optional, Union
import os

from client_app.app.modules.factory.graphics_factory import GraphicsFactory

class GraphicsService:
    """
    High-level service for Headless Graphics Generation.
    Allows programmatic generation of charts without UI interaction.
    """

    def __init__(self):
        self.factory = GraphicsFactory()

    async def process_file(self, file_path: str, prompt: str, output_path: Optional[str] = None) -> Union[str, bytes]:
        """
        Processes a file (CSV/Excel) and generates a chart based on the prompt.
        
        Args:
            file_path: Path to the data file.
            prompt: User description of the desired chart.
            output_path: If provided, saves the image to this path.
            
        Returns:
            str: Path to saved file if output_path is provided.
            bytes: Image bytes if output_path is None.
        """
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        img_bytes = await self.process_dataframe(df, prompt)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(img_bytes)
            return output_path
        
        return img_bytes

    async def process_dataframe(self, df: pd.DataFrame, prompt: str) -> bytes:
        """
        Processes a loaded DataFrame and generates a chart bytes.
        """
        # 1. Analyze
        metadata = self.factory.analyze_dataframe(df)
        
        # 2. Generate (Headless mode assumes direct generation, no clarification loop for simplicity in MVP)
        # Ideally, we could expose clarification via callback, but here we enforce generation.
        script = await self.factory.generate_script(metadata, prompt)
        
        # 3. Execute
        img_bytes = self.factory.execute_script(script, df)
        
        return img_bytes

# Singleton
graphics_service = GraphicsService()
