
from nicegui import ui
from typing import List, Dict, Any, Callable, Optional
from client_app.app.services.clarification_service import (
    ClarificationResult,
    ClarificationQuestion,
    ClarificationResponse,
    QuestionType
)

class ClarificationDialog:
    """
    Dialog component to handle clarification questions from the AI.
    """

    def __init__(self):
        self.dialog = ui.dialog()
        self.result_future = None
        self.responses: Dict[str, Any] = {}

    async def show(self, result: ClarificationResult) -> Optional[List[ClarificationResponse]]:
        """
        Shows the dialog with questions and awaits user responses.
        Returns List[ClarificationResponse] or None if cancelled/skipped.
        """
        self.responses = {}
        
        with self.dialog, ui.card().classes('w-full max-w-2xl'):
            ui.label("Clarificación Requerida").classes('text-xl font-bold mb-2')
            
            if result.reasoning:
                ui.markdown(f"**Razón:** {result.reasoning}").classes('text-gray-600 mb-4 bg-gray-100 p-2 rounded')

            container = ui.column().classes('w-full gap-4')
            
            with container:
                for question in result.questions:
                    self._render_question(question)

            with ui.row().classes('w-full justify-end mt-6 gap-2'):
                ui.button("Omitir y continuar", on_click=lambda: self.dialog.submit(None)).props('outline color=grey')
                ui.button("Enviar respuestas", on_click=lambda: self._submit(result.questions))

        return await self.dialog

    def _render_question(self, question: ClarificationQuestion):
        """Renders a single question based on its type."""
        with ui.column().classes('w-full'):
            label = f"{question.question}" + (" *" if question.required else "")
            ui.label(label).classes('font-medium')
            
            if question.hint:
                ui.label(question.hint).classes('text-sm text-gray-500 mb-1')

            # Initialize response value
            current_val = self.responses.get(question.id)
            
            if question.type == QuestionType.SINGLE_CHOICE:
                ui.radio(question.options or [], on_change=lambda e: self._update_response(question.id, e.value))
            
            elif question.type == QuestionType.MULTIPLE_CHOICE:
                # NiceGUI checkbox group logic or individual checkboxes
                # Using simple implementation for now
                if question.options:
                    # We store a set/list for multiple choice
                    self.responses[question.id] = [] 
                    with ui.column():
                        for opt in question.options:
                            ui.checkbox(opt, on_change=lambda e, o=opt: self._update_multi_response(question.id, o, e.value))

            elif question.type == QuestionType.FREE_TEXT:
                ui.textarea(label=None, on_change=lambda e: self._update_response(question.id, e.value)).classes('w-full')
            
            elif question.type == QuestionType.YES_NO:
                ui.switch("Sí / No", on_change=lambda e: self._update_response(question.id, e.value))
            
            elif question.type == QuestionType.FILE_UPLOAD:
                ui.label("(File upload not fully implemented in this demo)").classes('text-red-400 italic')

    def _update_response(self, q_id: str, value: Any):
        self.responses[q_id] = value

    def _update_multi_response(self, q_id: str, option: str, is_checked: bool):
        current_list = self.responses.get(q_id, [])
        if is_checked:
            if option not in current_list:
                current_list.append(option)
        else:
            if option in current_list:
                current_list.remove(option)
        self.responses[q_id] = current_list

    def _submit(self, questions: List[ClarificationQuestion]):
        # Validation
        for q in questions:
            if q.required:
                val = self.responses.get(q.id)
                # Check for empty string, None, or empty list
                if val is None or val == "" or (isinstance(val, list) and not val):
                    ui.notify(f"Falta respuesta: {q.question}", type='warning')
                    return

        # Build result
        final_responses = []
        for q_id, val in self.responses.items():
            final_responses.append(ClarificationResponse(question_id=q_id, answer=val))
        
        self.dialog.submit(final_responses)

async def show_clarification_dialog(
    result: ClarificationResult,
    on_submit: Callable[[List[ClarificationResponse]], None],
    on_skip: Callable[[], None]
):
    """
    Helper function to show the clarification dialog.
    Compatible with the call signature expected by etl_page.py.
    """
    dialog = ClarificationDialog()
    responses = await dialog.show(result)
    
    if responses:
        on_submit(responses)
    else:
        on_skip()
