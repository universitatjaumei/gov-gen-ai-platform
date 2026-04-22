"""
Componentes de formulario para configuracion de pasos del editor de flujos.
Prompt 3.x del plan de refactorizacion.
"""
from .api_fetch_form import render_api_fetch_form
from .email_send_form import render_email_send_form
from .extraction_form import render_extraction_form
from .custom_script_form import render_custom_script_form
from .generic_form import render_generic_form
from .report_generate_form import render_report_generate_form

__all__ = [
    "render_api_fetch_form",
    "render_email_send_form",
    "render_extraction_form",
    "render_custom_script_form",
    "render_generic_form",
    "render_report_generate_form",
]
