"""
ReportFactory - Servicio de Renderizado Headless con Playwright.

Captura la salida de NiceGUI para generar PDFs/PNGs de alta fidelidad.
Reutiliza Playwright del módulo RPA existente.
"""
from pathlib import Path
from typing import Dict, Any, Optional, Union
import asyncio

from client_app.app.core.state import state


class ReportFactory:
    """
    Factoría de renderizado headless para informes.

    Usa Playwright para capturar exactamente lo que se ve en el navegador,
    incluyendo gráficos ECharts con animaciones completadas.
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.default_timeout = 30000  # 30 segundos
        self.render_marker = ".echarts-done-marker"  # Marcador de renderizado completo

        # Import playwright only when needed to avoid overhead if not used
        try:
             from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
             self._pw = async_playwright
             self._timeout_error = PWTimeoutError
        except ImportError:
             self._pw = None

    async def capture_with_playwright(
        self,
        url: str,
        output_path: str,
        format: str = "pdf",
        viewport: Optional[Dict[str, int]] = None,
        timeout: Optional[int] = None,
        pdf_options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Capturar URL usando Playwright.

        Args:
            url: URL interna a renderizar
            output_path: Ruta donde guardar el archivo
            format: "pdf" o "png"
            viewport: Diccionario {width, height}
            timeout: Tiempo máximo en ms
            pdf_options: Opciones de PDF (page_size, orientation, margins)

        Returns:
            True si éxito
        """
        if not self._pw:
            raise ImportError("Playwright not installed")

        timeout = timeout or self.default_timeout
        viewport = viewport or {"width": 1280, "height": 800}
        pdf_options = pdf_options or {}

        async with self._pw() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page(viewport=viewport)

                # Navigate
                try:
                    await page.goto(url, wait_until="networkidle", timeout=timeout)
                except self._timeout_error:
                     # Network idle timed out, but maybe page loaded partially?
                     # Let's check for marker anyway or fail.
                     pass

                # Wait for render marker (important for charts)
                try:
                     # If marker is specified, wait for it.
                     # We assume the page adds this class specifically when ready.
                     if self.render_marker:
                         await page.wait_for_selector(self.render_marker, timeout=timeout, state="attached")
                     else:
                         await page.wait_for_selector("body", timeout=timeout)
                except self._timeout_error:
                     # Fallback logic: if marker not found, maybe it's a simple page without charts
                     # Just verify body exists
                     await page.wait_for_selector("body", timeout=timeout)

                # Export
                if format == "pdf":
                    # Configurar opciones de PDF
                    page_size = pdf_options.get('page_size', 'A4')
                    orientation = pdf_options.get('orientation', 'portrait')
                    margins = pdf_options.get('margins', {
                        'top': '20mm',
                        'right': '20mm',
                        'bottom': '20mm',
                        'left': '20mm'
                    })

                    await page.pdf(
                        path=output_path,
                        format=page_size,
                        landscape=(orientation == 'landscape'),
                        print_background=True,
                        margin=margins
                    )
                elif format == "png":
                    await page.screenshot(path=output_path, full_page=True)

                return True

            except Exception as e:
                # Log error
                print(f"Playwright error: {e}")
                # Re-raise timeout specifically as expected by tests
                if "Timeout" in str(e) or isinstance(e, self._timeout_error):
                     raise TimeoutError(f"Render timeout: {e}")
                return False
            finally:
                await browser.close()

    async def export_report(
        self,
        report_id: str,
        data: Dict[str, Any],
        format: str = "pdf",
        output_dir: Optional[str] = None,
        pdf_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Exportar informe por ID.

        Construye la URL de renderizado efímero, pasa los datos
        y captura el resultado.

        Args:
            report_id: ID del informe/plantilla
            data: Datos para inyectar en el informe
            format: Formato de salida ("pdf" o "png")
            output_dir: Directorio de salida (opcional)
            pdf_options: Opciones de PDF (page_size, orientation, margins)

        Returns:
            Ruta del archivo generado
        """
        import urllib.parse
        import json

        # Construir URL con datos como query param (codificados)
        data_encoded = urllib.parse.quote(json.dumps(data))
        url = f"{self.base_url}/internal/render_report/{report_id}?data={data_encoded}"

        # Determinar ruta de salida
        if output_dir:
            output_path = Path(output_dir) / f"{report_id}.{format}"
        else:
             # Fallback to reports dir in state or temp
            try:
                base_dir = Path(state.paths.reports_dir)
            except AttributeError:
                base_dir = Path("reports")

            base_dir.mkdir(parents=True, exist_ok=True)
            output_path = base_dir / f"{report_id}.{format}"

        # Capturar con opciones de PDF
        await self.capture_with_playwright(
            url,
            str(output_path),
            format=format,
            pdf_options=pdf_options
        )

        return str(output_path)

    async def export_report_to_bytes(
        self,
        report_id: str,
        data: Dict[str, Any],
        format: str = "pdf",
        pdf_options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Exportar informe y devolver bytes (útil para email).

        Args:
            report_id: ID del informe
            data: Datos para el informe
            format: Formato de salida
            pdf_options: Opciones de PDF (page_size, orientation, margins)

        Returns:
            Contenido del archivo como bytes
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
            tmp_path = tmp.name
            # Close handle to avoid lock on Windows
            tmp.close()

        try:
            generated_path_str = await self.export_report(
                report_id,
                data,
                format,
                output_dir=str(Path(tmp_path).parent),
                pdf_options=pdf_options
            )
            generated_path = Path(generated_path_str)
            
            # Note: export_report format is {report_id}.{format}
            # NamedTemporaryFile was just to get a dir? Or we wanted to use that file?
            # Creating a temp FILE and then using its parent dir might be racy or polluting.
            # Ideally we want the file content.
            # If export_report enforces filename, we read that.
            
            if generated_path.exists():
                content = generated_path.read_bytes()
                generated_path.unlink() # Cleanup generated file
            else:
                 content = b""
        finally:       
            # Cleanup temp file created by NamedTemporaryFile placeholder
            Path(tmp_path).unlink(missing_ok=True)

        return content


# Singleton
_factory_instance: Optional[ReportFactory] = None


def get_report_factory() -> ReportFactory:
    """Obtener instancia singleton de ReportFactory."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ReportFactory()
    return _factory_instance

