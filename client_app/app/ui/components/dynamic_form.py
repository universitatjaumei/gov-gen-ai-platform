from typing import Dict, Any, Callable, Optional, List
from nicegui import ui
from automatia_shared.contracts.ui_contract import (
    UIContract, InputType, InputDefinition
)
from unittest.mock import MagicMock
import re


def evaluate_field_visibility(contract: UIContract, field_name: str, current_data: Dict[str, Any]) -> bool:
    """
    Evalúa si un campo debe ser visible según sus dependencias.

    Args:
        contract: Contrato UI con definiciones
        field_name: Nombre del campo a evaluar
        current_data: Valores actuales de todos los campos

    Returns:
        True si el campo debe ser visible
    """
    field_def = next((f for f in contract.inputs if f.name == field_name), None)
    if not field_def:
        return True

    if not field_def.dependencies:
        return True  # Sin dependencias = siempre visible

    # Por defecto oculto si tiene dependencias de visibilidad
    has_visibility_dep = any(
        d.action.visible is not None for d in field_def.dependencies
    )

    if has_visibility_dep:
        # Oculto por defecto, visible solo si alguna dependencia lo activa
        for dep in field_def.dependencies:
            if dep.action.visible and contract._evaluate_dependency(dep, current_data):
                return True
        return False

    return True


def validate_field_constraints(contract: UIContract, field_name: str, value: Any) -> List[str]:
    """
    Valida un valor contra los constraints del campo.

    Returns:
        Lista de mensajes de error (vacía si válido)
    """
    errors = []
    field_def = next((f for f in contract.inputs if f.name == field_name), None)

    if not field_def or not field_def.constraints:
        return errors

    c = field_def.constraints

    # Validar min/max para números
    if isinstance(value, (int, float)):
        if c.min is not None and value < c.min:
            errors.append(f"El valor debe ser al menos {c.min}")
        if c.max is not None and value > c.max:
            errors.append(f"El valor supera el máximo de {c.max}")

    # Validar longitud para strings
    if isinstance(value, str):
        if c.min_length is not None and len(value) < c.min_length:
            errors.append(f"Mínimo {c.min_length} caracteres")
        if c.max_length is not None and len(value) > c.max_length:
            errors.append(f"Máximo {c.max_length} caracteres")
        if c.regex:
            if not re.match(c.regex, value):
                errors.append("El formato no es válido")

    return errors


class DynamicExecutorForm(ui.card):
    """
    Componente que renderiza un formulario dinámico basado en un UIContract.

    Características:
    - Reactividad: Campos se muestran/ocultan según Dependency
    - Validación: Constraints se validan en tiempo real
    - Accesibilidad: Errores visibles bajo cada campo
    """

    def __init__(self, contract: UIContract, on_submit: Optional[Callable[[Dict[str, Any]], None]] = None):
        super().__init__()
        self.contract = contract
        self.on_submit = on_submit

        self.params: Dict[str, Any] = {}
        self.inputs_map: Dict[str, Any] = {}  # name -> ui element
        self.containers_map: Dict[str, Any] = {}  # name -> container (for visibility)
        self.error_labels: Dict[str, Any] = {}  # name -> error label element
        self.has_errors: bool = False

        # Initialize defaults
        for inp in self.contract.inputs:
            self.params[inp.name] = inp.default

        self.build_form()

    def build_form(self):
        with self:
            ui.markdown(f"### Configuración de Ejecución (v{self.contract.version})")

            with ui.column().classes('w-full gap-4'):
                for inp in self.contract.inputs:
                    self._render_input_container(inp)

            with ui.row().classes('w-full justify-end mt-4'):
                self.submit_btn = ui.button(
                    "Ejecutar",
                    on_click=self.handle_submit
                ).props('color=primary icon=play_arrow')

    def _render_input_container(self, inp: InputDefinition):
        """Renderiza un campo dentro de un contenedor controlable."""
        # Evaluar visibilidad inicial
        is_visible = evaluate_field_visibility(self.contract, inp.name, self.params)

        # Contenedor para control de visibilidad
        container = ui.column().classes('w-full')
        container.visible = is_visible
        self.containers_map[inp.name] = container

        with container:
            self._render_input(inp)

    def _render_input(self, inp: InputDefinition):
        """Renderiza el control específico según el tipo."""
        label = f"{inp.label}{' *' if inp.required else ''}"

        # Crear elemento según tipo
        if inp.type in [InputType.STR, InputType.SECRET]:
            element = ui.input(
                label=label,
                password=(inp.type == InputType.SECRET),
                placeholder=inp.description,
                on_change=lambda e, name=inp.name: self._on_field_change(name, e.value)
            ).bind_value(self.params, inp.name).classes('w-full')

            # Añadir validación de constraints
            if inp.constraints and inp.constraints.regex:
                element.validation = {
                    'Formato inválido': lambda v: bool(re.match(inp.constraints.regex, v or ''))
                }

        elif inp.type in [InputType.INT, InputType.FLOAT]:
            element = ui.number(
                label=label,
                format='%.0f' if inp.type == InputType.INT else '%.2f',
                min=inp.constraints.min if inp.constraints else None,
                max=inp.constraints.max if inp.constraints else None,
                on_change=lambda e, name=inp.name: self._on_field_change(name, e.value)
            ).bind_value(self.params, inp.name).classes('w-full')

        elif inp.type == InputType.BOOL:
            element = ui.switch(
                label,
                on_change=lambda e, name=inp.name: self._on_field_change(name, e.value)
            ).bind_value(self.params, inp.name)

        elif inp.type == InputType.SELECT:
            element = ui.select(
                label=label,
                options=inp.options or [],
                on_change=lambda e, name=inp.name: self._on_field_change(name, e.value)
            ).bind_value(self.params, inp.name).classes('w-full')

        elif inp.type == InputType.FILE:
            with ui.row().classes('w-full items-center gap-2'):
                element = ui.input(
                    label=f"{label} (Ruta)",
                    placeholder="Seleccione archivo..."
                ).bind_value(self.params, inp.name).classes('flex-grow')
                ui.upload(
                    auto_upload=True,
                    on_upload=lambda e, name=inp.name: self._handle_upload(e, name),
                    max_files=1
                ).props('flat round dense icon=upload')

        else:
            element = ui.input(label=label).bind_value(self.params, inp.name).classes('w-full')

        self.inputs_map[inp.name] = element

        # Label para errores de validación
        error_label = ui.label('').classes('text-red-500 text-xs mt-1')
        error_label.visible = False
        self.error_labels[inp.name] = error_label

    def _on_field_change(self, field_name: str, value: Any):
        """Callback cuando cualquier campo cambia."""
        self.params[field_name] = value

        # 1. Actualizar visibilidad de campos dependientes
        self._update_all_visibility()

        # 2. Validar constraints del campo actual
        self._validate_field(field_name)

        # 3. Actualizar estado del botón submit
        self._update_submit_state()

    def _update_all_visibility(self):
        """Re-evalúa la visibilidad de todos los campos."""
        for inp in self.contract.inputs:
            if inp.name in self.containers_map:
                is_visible = evaluate_field_visibility(
                    self.contract, inp.name, self.params
                )
                self.containers_map[inp.name].visible = is_visible

    def _validate_field(self, field_name: str):
        """Valida un campo y muestra/oculta errores."""
        value = self.params.get(field_name)
        errors = validate_field_constraints(self.contract, field_name, value)

        if field_name in self.error_labels:
            if errors:
                self.error_labels[field_name].text = errors[0]
                self.error_labels[field_name].visible = True
            else:
                self.error_labels[field_name].visible = False

    def _update_submit_state(self):
        """Deshabilita el botón si hay errores de validación."""
        self.has_errors = any(
            label.visible for label in self.error_labels.values()
        )
        self.submit_btn.props(f'disable={self.has_errors}')

    def _handle_upload(self, e, field_name: str):
        """Maneja subida de archivos."""
        ui.notify(f"Archivo recibido: {e.name}")
        self.params[field_name] = f"uploads/{e.name}"
        if field_name in self.inputs_map:
            self.inputs_map[field_name].value = f"uploads/{e.name}"

    def handle_submit(self):
        """Procesa el envío del formulario."""
        if self.has_errors:
            ui.notify("Corrija los errores antes de continuar", type='negative')
            return

        try:
            # Filtrar campos ocultos (no enviar datos de campos invisibles)
            visible_params = {
                name: value for name, value in self.params.items()
                if self.containers_map.get(name, MagicMock(visible=True)).visible
            }

            validated = self.contract.validate_inputs(visible_params)
            ui.notify("Validación exitosa", type='positive')

            if self.on_submit:
                self.on_submit(validated)

        except ValueError as e:
            ui.notify(str(e), type='negative')

    def get_values(self) -> Dict[str, Any]:
        """Retorna valores actuales del formulario."""
        return self.params

