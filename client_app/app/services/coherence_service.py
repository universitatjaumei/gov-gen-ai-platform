from typing import List, Dict, Any

class CoherenceService:
    """
    The 'Coherence Assistant' that guides the user to fix problems.
    Translates 'Issues' (Health/Privacy) into 'SuggestedAction' (UI).
    """
    
    def analyze_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analiza una lista de problemas (técnicos o de privacidad) y los traduce
        en acciones sugeridas para el usuario en la interfaz.
        """
        suggestions = []
        
        for issue in issues:
            if issue['type'] == 'MISSING_VAR':
                suggestions.append({
                    'title': "Variable no encontrada",
                    'description': f"El paso actual necesita '{issue.get('var_name')}' pero no existe. ¿Quieres crearlo?",
                    'action_label': "Crear paso de extracción",
                    'action_type': "CREATE_STEP",
                    'action_payload': {'output_var': issue.get('var_name')},
                    'severity': 'high'
                })
            
            elif issue['type'] == 'PRIVACY_RISK':
                 # Prompt 8: Decision Card Logic
                 suggestions.append({
                    'title': "Decisión de Privacidad",
                    'description': f"Estás enviando datos sensibles ('{issue.get('var_name')}') a un sistema externo.",
                    'action_label': "Opciones de Seguridad",
                    'action_type': "DECISION_REQUIRED",
                    'severity': 'high',
                    'options': [
                        {
                            'label': "Anonimizar Datos",
                            'type': "ANONYMIZE_VAR",
                            'payload': {'target_var': issue.get('var_name')}
                        },
                        {
                            'label': "Confío en este destino",
                            'type': "GRANT_CONSENT",
                            'payload': {'step_index': issue.get('step_index')} # We need step index to update metadata
                        }
                    ]
                })
                
        return suggestions
