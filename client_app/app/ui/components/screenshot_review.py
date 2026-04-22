
"""
Screenshot Review Dialog Component.

Muestra una captura de pantalla al usuario para que apruebe o rechace
su envío al Brain (LLM multimodal) antes de procesarla.
"""
import asyncio
import base64
from typing import Optional, Union

from nicegui import ui

from client_app.app.core.state import state


class ScreenshotReviewDialog:
    """
    Diálogo modal para revisar y aprobar capturas de pantalla.

    Uso:
        dialog = ScreenshotReviewDialog(image_bytes, url)
        dialog.show()
        approved = await dialog.wait_for_result()
    """

    def __init__(
        self,
        image_data: Union[bytes, str],
        source_url: str = "",
        title: Optional[str] = None
    ):
        """
        Args:
            image_data: Imagen como bytes o string base64
            source_url: URL de origen de la captura (para contexto)
            title: Título personalizado del diálogo
        """
        self.source_url = source_url
        self.result: Optional[bool] = None
        self._result_event = asyncio.Event()
        self._dialog = None

        # Normalizar imagen a base64
        if isinstance(image_data, bytes):
            self.image_base64 = base64.b64encode(image_data).decode()
        else:
            self.image_base64 = image_data

        # Textos (i18n ready)
        t = state.i18n.t if hasattr(state, 'i18n') else lambda x: None
        self.title = title or t('screenshot_review_title') or "Revisión de Captura"
        self.warning_text = t('screenshot_review_warning') or (
            "Esta imagen será enviada para su procesamiento. "
            "Verifique que NO contiene datos sensibles o confidenciales "
            "(DNI, contraseñas, saldos, datos personales)."
        )
        self.approve_text = t('screenshot_approve') or "Aprobar y Enviar"
        self.reject_text = t('screenshot_reject') or "Cancelar"

    def _on_approve(self):
        """Handler para botón de aprobar."""
        self.result = True
        self._result_event.set()
        if self._dialog:
            self._dialog.close()

    def _on_reject(self):
        """Handler para botón de rechazar."""
        self.result = False
        self._result_event.set()
        if self._dialog:
            self._dialog.close()

    async def wait_for_result(self) -> bool:
        """
        Espera asíncronamente a que el usuario tome una decisión.

        Returns:
            True si aprobó, False si rechazó
        """
        await self._result_event.wait()
        return self.result

    def show(self):
        """Muestra el diálogo modal."""
        with ui.dialog() as self._dialog, ui.card().classes('w-full max-w-4xl'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(self.title).classes('text-xl font-bold')
                if self.source_url:
                    ui.label(self.source_url[:50] + "..." if len(self.source_url) > 50 else self.source_url).classes('text-sm text-gray-500')

            # Warning banner
            with ui.card().classes('w-full bg-amber-50 border border-amber-300 p-4 mb-4'):
                with ui.row().classes('items-start gap-3'):
                    ui.icon('warning', color='amber', size='md')
                    ui.label(self.warning_text).classes('text-amber-800')

            # Image container with scroll
            with ui.scroll_area().classes('w-full h-96 border rounded'):
                ui.image(f'data:image/png;base64,{self.image_base64}').classes('max-w-full')

            # Action buttons
            with ui.row().classes('w-full justify-end gap-4 mt-4'):
                ui.button(
                    self.reject_text,
                    on_click=self._on_reject,
                    color='red'
                ).props('outline')

                ui.button(
                    self.approve_text,
                    on_click=self._on_approve,
                    color='green'
                )

        self._dialog.open()
        return self


async def request_screenshot_approval(
    image_data: Union[bytes, str],
    source_url: str = ""
) -> bool:
    """
    Función helper para solicitar aprobación de captura.

    Args:
        image_data: Imagen como bytes o base64
        source_url: URL de origen

    Returns:
        True si el usuario aprobó, False si rechazó
    """
    dialog = ScreenshotReviewDialog(image_data, source_url)
    dialog.show()
    return await dialog.wait_for_result()
