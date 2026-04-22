from typing import List, Dict, Any
from automatia_shared.dtos import FlowSpec

class WorkflowHealthService:
    """
    Validates workflow steps to ensure data integrity.
    Functions as the 'Active Guardian' (Cerebro) of the system.
    """
    
    def check_step(self, flow: FlowSpec, step_index: int) -> List[Dict[str, Any]]:
        """
        Analyzes a specific step to see if its requirements are met by previous steps.
        Returns a list of issues found.
        """
        issues = []
        
        # 1. Bounds check
        if step_index < 0 or step_index >= len(flow.steps):
            return []
            
        current_step = flow.steps[step_index]
        
        # 2. Collect available variables from PREVIOUS steps (0 to step_index - 1)
        available_vars = set()
        for i in range(step_index):
            step = flow.steps[i]
            if step.outputs:
                for out_var in step.outputs:
                    available_vars.add(out_var)
                    
        # 3. Check inputs required by CURRENT step
        if current_step.inputs:
            for required_var in current_step.inputs:
                if required_var not in available_vars:
                    # ISSUE FOUND: Missing Variable
                    issues.append({
                        'type': 'MISSING_VAR',
                        'severity': 'CRITICAL',
                        'msg': f"Falta la variable requerida: '{required_var}'",
                        'var_name': required_var
                    })
                    
        return issues
