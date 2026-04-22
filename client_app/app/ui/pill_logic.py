from typing import List, Optional
from dataclasses import dataclass
from automatia_shared.dtos import FlowSpec, TaskSpec

@dataclass
class DataPill:
    """
    Representa una 'píldora de datos' o variable proveniente de un paso previo.
    Permite referenciar salidas de un paso como entradas de otro mediante una sintaxis amigable.
    """
    label: str  # Etiqueta legible de la variable
    origin_step: str  # ID o nombre del paso que genera el dato
    var_name: str  # Nombre técnico de la variable
    
    @property
    def reference(self) -> str:
        """Devuelve la referencia técnica formateada (ej: {{ID_PASO.variable}})."""
        return f"{{{{{self.origin_step}.{self.var_name}}}}}"
        
    def get_display_text(self) -> str:
        """Devuelve una etiqueta descriptiva para mostrar en la interfaz (ej: [PASO] Variable)."""
        return f"[{self.origin_step}] {self.label}"

class PillProvider:
    """
    Proveedor de variables disponibles (DataPills) para un punto específico del flujo.
    Filtra qué datos son accesibles basándose en el orden de ejecución de los pasos.
    """
    def __init__(self, flow: FlowSpec):
        self.flow = flow

    def get_available_pills(self, current_step_index: int) -> List[DataPill]:
        """
        Calcula qué variables están disponibles para ser usadas en un paso determinado.
        Solo permite el acceso a salidas de pasos que ocurren cronológicamente antes.

        Args:
            current_step_index: Índice del paso actual en el flujo.

        Returns:
            Lista de objetos DataPill disponibles.
        """
        available = []
        # Solo podemos usar variables de pasos anteriores
        for i in range(current_step_index):
            if i >= len(self.flow.steps):
                break
                
            step = self.flow.steps[i]
            
            # Identificador del paso: Intentamos usar ID si existe (aunque TaskSpec actual no lo tiene obligatorio)
            # Usaremos el nombre normalizado o un indice si no hay ID.
            # En el futuro TaskSpec debera tener ID.
            # Hack temporal: Si step tiene atributo 'id', usalo. Si no, usa Name slugified o Indice.
            step_id = getattr(step, 'id', None)
            if not step_id:
                # Fallback: Usar nombre como ID fake
                step_id = step.name.replace(" ", "_").upper()
            
            if step.outputs:
                for out in step.outputs:
                    available.append(DataPill(
                        label=out,
                        origin_step=str(step_id),
                        var_name=out
                    ))
        return available
