"""
EmailReviewPanel - Panel de revisión y selección de correos.

Permite al usuario revisar, seleccionar y editar el contenido de los
correos antes de enviarlos a un LLM o procesamiento posterior.

Funcionalidades:
- Lista de correos con checkboxes para selección
- Vista previa del cuerpo de cada correo (colapsable)
- Textarea editable con contexto concatenado
- Contador de caracteres/tokens
- Botones de selección rápida (todos/ninguno)
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from nicegui import ui

from client_app.app.services.email_body_utils import clean_email_body, build_llm_context


class EmailReviewPanelState:
    """Estado interno del panel de revisión."""

    def __init__(self):
        self.emails: List[Dict[str, Any]] = []
        self.selected_ids: set = set()
        self.context_text: str = ""
        self.show_preview: Dict[int, bool] = {}
        self.is_loading: bool = False
        self.max_chars: int = 50000


def email_review_panel(
    emails: List[Dict[str, Any]],
    on_submit: Optional[Callable[[str, List[int]], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
    max_chars: int = 50000,
    title: str = "Revisión de Correos",
    submit_label: str = "Continuar",
    show_clean_option: bool = True
) -> EmailReviewPanelState:
    """
    Renderiza el panel de revisión de correos.

    Args:
        emails: Lista de diccionarios con datos de correos
                Cada dict debe tener: id, sender, subject, date, body_plain
        on_submit: Callback cuando el usuario confirma (recibe contexto y IDs seleccionados)
        on_cancel: Callback cuando el usuario cancela
        max_chars: Límite máximo de caracteres para el contexto
        title: Título del panel
        submit_label: Etiqueta del botón de confirmación
        show_clean_option: Si mostrar checkbox para aplicar limpieza automática

    Returns:
        Estado del panel para control externo
    """
    state = EmailReviewPanelState()
    state.emails = emails
    state.max_chars = max_chars
    state.selected_ids = {e.get('id', i) for i, e in enumerate(emails)}

    # Inicializar previews cerradas
    for i, email in enumerate(emails):
        state.show_preview[email.get('id', i)] = False

    apply_cleaning = {'value': True}

    def update_context():
        """Actualiza el texto del contexto basado en la selección."""
        selected_emails = [
            e for e in state.emails
            if e.get('id', state.emails.index(e)) in state.selected_ids
        ]

        if apply_cleaning['value']:
            emails_data = [
                {
                    'sender': e.get('sender', ''),
                    'subject': e.get('subject', ''),
                    'date': e.get('date', ''),
                    'body_plain': e.get('body_plain', '')
                }
                for e in selected_emails
            ]
            state.context_text = build_llm_context(emails_data, state.max_chars)
        else:
            # Sin limpieza: concatenar directamente
            parts = []
            for e in selected_emails:
                parts.append(f"--- Correo de {e.get('sender', '')} ---")
                parts.append(f"Asunto: {e.get('subject', '')}")
                parts.append(f"Fecha: {e.get('date', '')}")
                parts.append("")
                parts.append(e.get('body_plain', ''))
                parts.append("")
            state.context_text = "\n".join(parts)[:state.max_chars]

        context_area.refresh()
        char_counter.refresh()

    def toggle_email(email_id: int, selected: bool):
        """Alterna la selección de un correo."""
        if selected:
            state.selected_ids.add(email_id)
        else:
            state.selected_ids.discard(email_id)
        update_context()

    def select_all():
        """Selecciona todos los correos."""
        state.selected_ids = {e.get('id', i) for i, e in enumerate(state.emails)}
        email_list.refresh()
        update_context()

    def select_none():
        """Deselecciona todos los correos."""
        state.selected_ids = set()
        email_list.refresh()
        update_context()

    def toggle_preview(email_id: int):
        """Muestra/oculta la preview de un correo."""
        state.show_preview[email_id] = not state.show_preview.get(email_id, False)
        email_list.refresh()

    def handle_submit():
        """Maneja el envío del formulario."""
        if on_submit:
            selected_ids = list(state.selected_ids)
            on_submit(state.context_text, selected_ids)

    def handle_cancel():
        """Maneja la cancelación."""
        if on_cancel:
            on_cancel()

    # --- RENDER ---

    with ui.card().classes('w-full p-4 shadow-md'):
        # Header
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(title).classes('text-lg font-bold')
            with ui.row().classes('gap-2'):
                ui.button('Seleccionar todos', on_click=select_all).props('flat dense size=sm')
                ui.button('Deseleccionar todos', on_click=select_none).props('flat dense size=sm')

        # Lista de correos
        @ui.refreshable
        def email_list():
            with ui.scroll_area().classes('w-full h-64 border rounded p-2'):
                if not state.emails:
                    ui.label('No hay correos para revisar').classes('text-gray-500 italic')
                else:
                    for i, email in enumerate(state.emails):
                        email_id = email.get('id', i)
                        is_selected = email_id in state.selected_ids
                        is_preview_open = state.show_preview.get(email_id, False)

                        with ui.card().classes(
                            f'w-full mb-2 p-3 border {"border-blue-300 bg-blue-50" if is_selected else "border-gray-200"}'
                        ):
                            with ui.row().classes('w-full items-start gap-2'):
                                # Checkbox
                                ui.checkbox(
                                    value=is_selected,
                                    on_change=lambda e, eid=email_id: toggle_email(eid, e.value)
                                )

                                # Info del correo
                                with ui.column().classes('flex-grow gap-0'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(email.get('subject', 'Sin asunto')[:60]).classes(
                                            'font-medium text-sm truncate'
                                        )
                                        if email.get('attachments'):
                                            att_count = len(email.get('attachments', []))
                                            ui.badge(f'📎 {att_count}').props('color=amber')

                                    with ui.row().classes('items-center gap-4 opacity-70'):
                                        ui.label(email.get('sender', '')[:40]).classes('text-xs truncate')
                                        date_val = email.get('date', '')
                                        if isinstance(date_val, datetime):
                                            date_val = date_val.strftime('%Y-%m-%d %H:%M')
                                        ui.label(str(date_val)).classes('text-xs')

                                # Botón de preview
                                ui.button(
                                    icon='expand_more' if not is_preview_open else 'expand_less',
                                    on_click=lambda eid=email_id: toggle_preview(eid)
                                ).props('flat dense round size=sm')

                            # Preview del body
                            if is_preview_open:
                                body = email.get('body_plain', '')
                                if apply_cleaning['value']:
                                    body = clean_email_body(body)
                                preview = body[:500] + ('...' if len(body) > 500 else '')

                                with ui.card().classes('w-full mt-2 p-2 bg-gray-50 border'):
                                    ui.label(preview).classes('text-xs whitespace-pre-wrap font-mono')

        email_list()

        ui.separator().classes('my-4')

        # Opciones de limpieza
        if show_clean_option:
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.checkbox(
                    'Aplicar limpieza automática (eliminar firmas y hilos)',
                    value=apply_cleaning['value'],
                    on_change=lambda e: (apply_cleaning.update({'value': e.value}), update_context())
                ).classes('text-xs')

        # Área de contexto editable
        ui.label('Contexto para LLM (editable)').classes('font-medium text-sm mb-1')

        @ui.refreshable
        def context_area():
            ui.textarea(
                value=state.context_text,
                on_change=lambda e: setattr(state, 'context_text', e.value)
            ).classes('w-full h-48 font-mono text-xs').props('outlined')

        context_area()

        # Contador de caracteres
        @ui.refreshable
        def char_counter():
            char_count = len(state.context_text)
            color = 'text-green-600' if char_count < state.max_chars * 0.8 else (
                'text-amber-600' if char_count < state.max_chars else 'text-red-600'
            )
            ui.label(f'{char_count:,} / {state.max_chars:,} caracteres').classes(f'text-xs {color}')

        char_counter()

        # Botones de acción
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            if on_cancel:
                ui.button('Cancelar', on_click=handle_cancel).props('flat color=gray')
            ui.button(
                submit_label,
                icon='send',
                on_click=handle_submit
            ).props('unelevated color=primary').bind_enabled_from(
                state, 'selected_ids', backward=lambda x: len(x) > 0
            )

    # Inicializar contexto
    update_context()

    return state


async def email_review_dialog(
    emails: List[Dict[str, Any]],
    title: str = "Revisión de Correos",
    max_chars: int = 50000
) -> Optional[tuple[str, List[int]]]:
    """
    Muestra un diálogo modal para revisión de correos.

    Args:
        emails: Lista de correos a revisar
        title: Título del diálogo
        max_chars: Límite de caracteres

    Returns:
        Tupla (contexto_texto, ids_seleccionados) o None si se cancela
    """
    result = {'submitted': False, 'context': '', 'ids': []}

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl'):
        def on_submit(context: str, ids: List[int]):
            result['submitted'] = True
            result['context'] = context
            result['ids'] = ids
            dialog.close()

        def on_cancel():
            dialog.close()

        email_review_panel(
            emails=emails,
            on_submit=on_submit,
            on_cancel=on_cancel,
            max_chars=max_chars,
            title=title
        )

    dialog.open()
    await dialog

    if result['submitted']:
        return result['context'], result['ids']
    return None
