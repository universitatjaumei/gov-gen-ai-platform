
from typing import Dict, Any

class AnalysisPromptBuilder:
    """
    Builder for AI prompts related to data analysis and visualization suggestions.
    """

    def build_business_questions_prompt(self, df_metadata: Dict[str, Any]) -> str:
        """
        Constructs a prompt to ask the AI for relevant business questions based on the data.
        """
        return f"""
        You are a Data Analyst expert. Analyze the following dataset metadata and suggest 3-5 insightful business questions that could be answered with this data.
        
        DATA METADATA:
        {df_metadata}
        
        OUTPUT FORMAT:
        Return a JSON object with a key "questions" containing a list of strings.
        Example: {{ "questions": ["What is the trend of sales over time?", "Which category has the highest profit?"] }}
        """

    def build_visualization_suggestions_prompt(self, df_metadata: Dict[str, Any], question: str) -> str:
        """
        Constructs a prompt to ask for visualization suggestions for a specific question.
        """
        return f"""
        You are a Data Visualization expert. Based on the dataset and the user's question, suggest 1-3 suitable charts.
        
        DATA METADATA:
        {df_metadata}
        
        USER QUESTION:
        "{question}"
        
        OUTPUT FORMAT:
        Return a JSON object with a key "suggestions" containing a list of objects.
        Each object should have:
        - "type": Chart type (e.g., "bar", "line", "scatter", "pie")
        - "reason": Why this chart is suitable.
        - "description": Brief description of what axes/data to map.
        
        Example:
        {{ "suggestions": [ {{ "type": "bar", "reason": "Best for comparing categories", "description": "X-axis: Category, Y-axis: Value" }} ] }}
        """
