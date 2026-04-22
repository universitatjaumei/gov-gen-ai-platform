
import pandas as pd
from typing import List, Dict, Any
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

class PIIDetector:
    """
    Utility to detect PII in DataFrames using heuristics and NER.
    Wraps AnonymizerContext for UI consumption.
    """
    
    def __init__(self):
        self.ctx = AnonymizationContext()

    def scan_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Scans a DataFrame for PII and returns a list of field configurations.
        
        Args:
            df: DataFrame to scan (analyzes a sample).
            
        Returns:
            List of dicts with:
            - field: column name
            - type: detected PII type (or NONE)
            - is_sensitive: bool
            - recommended_strategy: 'masking', 'synthetic', etc.
            - confidence: float
        """
        if df is None or df.empty:
            return []
            
        # Analyze using the robust logic in AnonymizerContext
        analysis_results = self.ctx.analyze_fields(df)
        
        return analysis_results
