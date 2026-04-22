# client_app/app/ui/components/anonymizer_field_row.py
from typing import Dict, Any, Callable, Optional
from nicegui import ui

class AnonymizerFieldRow:
    """
    Componente de fila reactiva para la configuración de anonimización de un campo.
    """
    
    STRATEGY_MAP = {
        'masking': 'Ocultación (XXXX)',
        'initials': 'Iniciales (J.P.)',
        'aepd': 'Formato AEPD',
        'none': None
    }
    
    def __init__(
        self, 
        field_info: Dict[str, Any], 
        on_change: Optional[Callable[[Dict[str, Any]], None]] = None,
        initial_mode: Optional[str] = None
    ):
        """
        Inicializa la fila del campo.
        
        Args:
            field_info: Diccionario con la info del campo.
            on_change: Callback opcional.
            initial_mode: Estrategia inicial preseleccionada (MASK, INITIALS, AEPD).
        """
        self.field_info = field_info
        self.on_change = on_change
        
        # Estado interno
        self.active = field_info.get('is_sensitive', False)
        
        # Determine strategy text based on initial_mode
        self.strategy_text = self.STRATEGY_MAP.get('masking') # Default
        
        if initial_mode:
            # Map backend generic modes to our keys
            if initial_mode == 'INITIALS':
                self.strategy_text = self.STRATEGY_MAP.get('initials')
            elif initial_mode == 'AEPD':
                self.strategy_text = self.STRATEGY_MAP.get('aepd')
            elif initial_mode == 'MASK':
                self.strategy_text = self.STRATEGY_MAP.get('masking')
        
        self._build_ui()

    def _build_ui(self):
        """Construye la interfaz de la fila."""
        with ui.row().classes('w-full items-center p-2 border-b border-gray-100 hover:bg-blue-50 transition-colors'):
            # 1. Checkbox de activación
            self.checkbox = ui.checkbox(value=self.active, on_change=self._handle_change)
            
            # 2. Etiquetas de nombre y tipo
            with ui.column().classes('flex-grow gap-0'):
                ui.label(self.field_info['field']).classes('font-bold text-sm')
                
                type_name = self.field_info.get('type', 'NONE')
                icon = self._get_type_icon(type_name)
                ui.label(f"{icon} {type_name}").classes('text-xs text-gray-500 italic')

            # 3. Selector de estrategia (reactivo a la visibilidad)
            options = {
                self.STRATEGY_MAP['masking']: 'masking'
            }
            
            # Add Initials for PERSON
            if self.field_info.get('type') in ['PERSON', 'PERSON_NAME']:
                options['Iniciales (J.P.)'] = 'initials'
            
            # Add AEPD option if ID type
            if self.field_info.get('type') in ['ID', 'DNI', 'NIE', 'PASSPORT']:
                 options['Formato AEPD'] = 'aepd'
            
            # Create reverse map for this instance
            self.instance_reverse_map = {k: v for k, v in options.items()}
            
            # Ensure current value is valid for this type, else reset to masking
            if self.strategy_text not in options:
                self.strategy_text = self.STRATEGY_MAP['masking']
            
            self.select = ui.select(
                options=list(options.keys()), 
                value=self.strategy_text,
                on_change=self._handle_change
            ).classes('w-48').bind_visibility_from(self.checkbox, 'value')

    def _get_type_icon(self, type_name: str) -> str:
        """Retorna un icono representativo según el tipo detectado."""
        icons = {
            'EMAIL': '📧',
            'PERSON': '👤',
            'ID': '🆔',
            'NONE': '📄'
        }
        return icons.get(type_name, '📄')

    def _handle_change(self):
        """Maneja cualquier cambio en los controles y emite el evento."""
        self.active = self.checkbox.value
        self.strategy_text = self.select.value
        
        # Resolve strategy key
        strategy_key = self.instance_reverse_map.get(self.strategy_text, 'none')

        if self.on_change:
            # Reconstruir el estado actual
            state = {
                'field': self.field_info['field'],
                'active': self.active,
                'strategy': strategy_key if self.active else 'none',
                'type': self.field_info.get('type')
            }
            self.on_change(state)

    def get_state(self) -> Dict[str, Any]:
        """Retorna el estado actual del componente."""
        # Resolve strategy key
        # Safety check if instance_reverse_map exists (it should after init)
        rmap = getattr(self, 'instance_reverse_map', self.REVERSE_STRATEGY_MAP)
        strategy_key = rmap.get(self.strategy_text, 'none')

        return {
            'field': self.field_info['field'],
            'active': self.active,
            'strategy': strategy_key if self.active else 'none',
            'type': self.field_info.get('type')
        }
