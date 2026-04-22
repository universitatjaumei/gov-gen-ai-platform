import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List

# ODF imports for ODT generation
from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties, TableCellProperties
from odf.text import P, H
from odf.table import Table as OdfTable, TableColumn, TableRow, TableCell

# ReportLab imports
from reportlab.lib.pagesizes import letter, A4, A3, landscape, portrait
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# HTML Backend imports
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class ReportFactory:
    """
    Factory for generating PDF reports using multiple backends:
    - 'reportlab' (default): Direct PDF generation, no HTML (Fast, No dependencies)
    - 'html': Generate HTML from Jinja2 templates, optionally convert to PDF (Editable, Flexible)
    
    Migration from WeasyPrint to ReportLab for better Windows compatibility
    (no GTK+3 dependencies required).
    """
    
    def __init__(self, backend: str = "reportlab", templates_dir: str = None):
        """
        Initialize ReportFactory.
        
        Args:
            backend: PDF backend. Options: 'reportlab', 'html'
            templates_dir: Path to Jinja2 templates (only for 'html' backend)
        """
        self.backend = backend
        
        if backend == "html":
            if templates_dir:
                self.templates_dir = Path(templates_dir)
            else:
                # Default: client_app/data/templates/reports
                self.templates_dir = BASE_DIR / "data" / "templates" / "reports"
            
            if not self.templates_dir.exists():
                # Try creating it if it doesn't exist? Or just fail? 
                # Better to warn or ensure creation if inside app data.
                # For now, let's just log and rely on caller or setup.
                logger.warning(f"Templates directory not found: {self.templates_dir}")
                # We can try to rely on package loading, but Filesystem is safer for user editable templates.
            
            if self.templates_dir.exists():
                self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
                logger.info(f"ReportFactory initialized with HTML backend, templates: {self.templates_dir}")
            else:
                 # Fallback/Error state
                 self.env = None
        else:
            logger.info(f"ReportFactory initialized with backend: {backend}")
    
    def generate_pdf(self, context: Dict[str, Any], output_path: str,
                     template_name: Optional[str] = None,
                     export_html: bool = False, html_path: str = None,
                     page_options: Optional[Dict[str, Any]] = None):
        """
        Generate PDF report from context data.

        Args:
            context: Dictionary with report data (title, summary, sections, table_data...)
            output_path: Path where PDF will be saved
            export_html: If True and backend='html', also save HTML file
            html_path: Custom path for HTML export (default: output_path.replace('.pdf', '.html'))
            page_options: Page configuration dict with keys:
                - page_size: 'A4', 'Letter', 'A3' (default: 'A4')
                - orientation: 'portrait', 'landscape' (default: 'portrait')
        """
        page_options = page_options or {}

        if self.backend == "reportlab":
            return self._generate_with_reportlab(context, output_path, page_options)
        elif self.backend == "html":
            return self._generate_with_html(context, output_path, template_name, export_html, html_path, page_options)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def _generate_with_reportlab(self, context: Dict[str, Any], output_path: str,
                                   page_options: Optional[Dict[str, Any]] = None):
        """Generate PDF using ReportLab."""
        output = Path(output_path)
        page_options = page_options or {}

        # Create parent directories if needed
        output.parent.mkdir(parents=True, exist_ok=True)

        # Determine page size and orientation
        page_size_name = page_options.get('page_size', 'A4').upper()
        orientation_name = page_options.get('orientation', 'portrait').lower()

        # Map page size names to ReportLab page sizes
        page_sizes = {
            'A4': A4,
            'A3': A3,
            'LETTER': letter
        }
        base_pagesize = page_sizes.get(page_size_name, A4)

        # Apply orientation
        if orientation_name == 'landscape':
            pagesize = landscape(base_pagesize)
        else:
            pagesize = portrait(base_pagesize)

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output),
            pagesize=pagesize,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        custom_styles = context.get("styles", {})
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=custom_styles.get('title_size', 24),
            textColor=colors.HexColor(custom_styles.get('title_color', '#000000'))
                if 'title_color' in custom_styles else colors.black,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # --- LOGO (if provided) ---
        if 'logo_path' in context and context['logo_path']:
            logo_path = Path(context['logo_path'])
            if logo_path.exists():
                try:
                    # ReportLab Image
                    logo = RLImage(str(logo_path), width=2*inch, height=0.8*inch)
                    elements.append(logo)
                    elements.append(Spacer(1, 12))
                except Exception as e:
                    logger.warning(f"Could not embed logo: {e}")
        
        # --- TITLE ---
        if 'title' in context:
            title = Paragraph(context['title'], title_style)
            elements.append(title)
            elements.append(Spacer(1, 12))
        
        # --- SUBTITLE ---
        if 'subtitle' in context:
            subtitle = Paragraph(context['subtitle'], styles['Heading2'])
            elements.append(subtitle)
            elements.append(Spacer(1, 12))
        
        # --- DATE ---
        if 'date' in context:
            date_text = Paragraph(f"<i>{context['date']}</i>", styles['Normal'])
            elements.append(date_text)
            elements.append(Spacer(1, 20))
        
        # --- SUMMARY ---
        if 'summary' in context:
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['BodyText'],
                fontSize=custom_styles.get('body_size', 12),
                textColor=colors.HexColor(custom_styles.get('body_color', '#000000'))
                    if 'body_color' in custom_styles else colors.black,
                alignment=TA_JUSTIFY
            )
            summary = Paragraph(context['summary'], summary_style)
            elements.append(summary)
            elements.append(Spacer(1, 20))
        
        # --- SECTIONS ---
        if 'sections' in context:
            for section in context['sections']:
                heading = Paragraph(section['heading'], styles['Heading2'])
                elements.append(heading)
                elements.append(Spacer(1, 8))
                
                content = Paragraph(section['content'], styles['BodyText'])
                elements.append(content)
                elements.append(Spacer(1, 15))
        
        # --- TABLE (Pandas DataFrame) ---
        if 'table_data' in context:
            df = context['table_data']
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Convert DataFrame to list of lists including header
                table_data = [df.columns.tolist()] + df.values.tolist()
                
                # Create Table
                table = Table(table_data)
                
                # Style the table
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(elements)
        
        logger.info(f"PDF successfully generated at {output}")
        return str(output)

    def _generate_with_html(self, context: Dict[str, Any], output_path: str,
                           template_name: Optional[str] = None,
                           export_html: bool = False, html_path: str = None,
                           page_options: Optional[Dict[str, Any]] = None):
        """Generate PDF from HTML template using Playwright."""
        if not self.env:
            raise ValueError("HTML backend not initialized correctly (templates dir not found).")

        output = Path(output_path)
        page_options = page_options or {}
        output.parent.mkdir(parents=True, exist_ok=True)

        # Page configuration
        page_size = page_options.get('page_size', 'A4')
        orientation = page_options.get('orientation', 'portrait')
        is_landscape = orientation.lower() == 'landscape'

        # 1. Render HTML from template
        html_content = self._render_html_template(context, template_name)

        # 2. Export HTML if requested
        if export_html or html_path:
            if not html_path:
                html_path = str(output).replace('.pdf', '.html')

            Path(html_path).write_text(html_content, encoding='utf-8')
            logger.info(f"HTML exported to {html_path}")

        # 3. Convert HTML to PDF using Playwright
        with sync_playwright() as p:
            # Reutilizamos browser si es posible o lanzamos uno nuevo
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content)
            page.pdf(
                path=str(output),
                format=page_size,
                landscape=is_landscape,
                print_background=True,
                margin={'top': '20mm', 'right': '20mm', 'bottom': '20mm', 'left': '20mm'}
            )
            browser.close()

        logger.info(f"PDF successfully generated at {output}")
        return str(output)
    
    def _render_html_template(self, context: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """Render Jinja2 HTML template with context data."""
        # Configurar contexto mutable
        render_context = context.copy()
        
        # Ensure styles exists for template safety
        if 'styles' not in render_context:
            render_context['styles'] = {}
        
        # Convert DataFrame to HTML table if present
        if 'table_data' in context:
            df = context['table_data']
            if isinstance(df, pd.DataFrame) and not df.empty:
                render_context['table_html'] = df.to_html(
                    classes='table',
                    index=False,
                    border=0
                )
        
        # Render template
        template_to_use = template_name if template_name else 'base_report.html'
        template = self.env.get_template(template_to_use)
        html = template.render(**render_context)
        
        return html
    
    def generate_odt(self, context: Dict[str, Any], output_path: str) -> str:
        """
        Genera documento ODT editable.

        Args:
            context: Diccionario con datos del informe
                - title: Título del documento
                - subtitle: Subtítulo (opcional)
                - date: Fecha (opcional)
                - summary: Resumen (opcional)
                - sections: Lista de {heading, content}
                - table_data: pd.DataFrame (opcional)
                - styles: Dict con configuración visual
                - logo_path: Ruta a imagen de logo (opcional)
            output_path: Ruta donde guardar el .odt

        Returns:
            str: Ruta al archivo generado
        """
        return self._generate_with_odfpy(context, output_path)

    def generate_report(self, context: Dict[str, Any], output_path: str, format: str = "pdf") -> str:
        """
        Método unificado para generar reportes.

        Args:
            format: "pdf", "odt", "html"
        """
        if format == "odt" or output_path.endswith('.odt'):
            return self.generate_odt(context, output_path)
        elif format == "html" or output_path.endswith('.html'):
            return self.export_html(context, output_path)
        else:
            return self.generate_pdf(context, output_path)

    def _generate_with_odfpy(self, context: Dict[str, Any], output_path: str) -> str:
        """
        Genera documento ODT usando odfpy.

        Estructura del documento:
        1. Título (H1)
        2. Subtítulo (H2, opcional)
        3. Fecha
        4. Resumen (párrafo justificado)
        5. Secciones (H2 + párrafos)
        6. Tabla de datos (si hay DataFrame)
        """
        doc = OpenDocumentText()
        styles_config = context.get('styles', {})

        # === DEFINIR ESTILOS ===
        
        # 1. Título
        title_config = {"size": 24, "bold": True, "align": "center"}
        if 'title_color' in styles_config: title_config['color'] = styles_config['title_color']
        if 'title_size' in styles_config: title_config['size'] = styles_config['title_size']
        
        title_style = Style(name="Title", family="paragraph")
        self._apply_style_from_config(title_style, title_config)
        doc.styles.addElement(title_style)

        # 2. Heading 2
        h2_config = {"size": 16, "bold": True}
        h2_style = Style(name="Heading2", family="paragraph")
        self._apply_style_from_config(h2_style, h2_config)
        doc.styles.addElement(h2_style)
        
        # 3. Cuerpo (Summary/Content)
        body_config = {"size": 12}
        if 'body_size' in styles_config: body_config['size'] = styles_config['body_size']
        if 'body_color' in styles_config: body_config['color'] = styles_config['body_color']
        
        body_style = Style(name="BodyText", family="paragraph")
        self._apply_style_from_config(body_style, body_config)
        doc.styles.addElement(body_style)

        # 4. Tabla - Styles Auto (usados en automaticstyles para celdas)
        # Header
        header_bg = styles_config.get('table_header_bg', '#808080')
        header_config = {"bold": True, "color": "#FFFFFF", "bg_color": header_bg, "align": "center"}
        self.header_style = Style(name="TableHeader", family="table-cell")
        self._apply_style_from_config(self.header_style, header_config)
        doc.automaticstyles.addElement(self.header_style)
        
        # Cell Normal
        border_color = styles_config.get('table_border', '#000000')
        cell_config = {"border": f"0.05pt solid {border_color}", "align": "center"}
        self.cell_style = Style(name="TableCell", family="table-cell")
        self._apply_style_from_config(self.cell_style, cell_config)
        doc.automaticstyles.addElement(self.cell_style)
        
        # === CONTENIDO ===
        # Título
        if 'title' in context:
            p = P(stylename=title_style, text=context['title'])
            doc.text.addElement(p)

        # Subtítulo (using Heading 2 style)
        if 'subtitle' in context:
             h = H(outlinelevel=2, stylename=h2_style, text=context['subtitle'])
             doc.text.addElement(h)
             
        # Fecha
        if 'date' in context:
            p = P(stylename=body_style, text=f"Fecha: {context['date']}")
            doc.text.addElement(p)
            
        # Resumen
        if 'summary' in context:
            p = P(stylename=body_style, text=context['summary'])
            doc.text.addElement(p)

        # Secciones
        if 'sections' in context:
            for section in context['sections']:
                h = H(outlinelevel=2, stylename=h2_style, text=section['heading'])
                doc.text.addElement(h)
                p = P(stylename=body_style, text=section['content'])
                doc.text.addElement(p)

        # === TABLA ===
        if 'table_data' in context:
            df = context['table_data']
            if isinstance(df, pd.DataFrame) and not df.empty:
                table = self._dataframe_to_odt_table(doc, df, self.header_style, self.cell_style)
                doc.text.addElement(table)

        # Guardar
        doc.save(output_path)
        return output_path

    def _dataframe_to_odt_table(self, doc, df: pd.DataFrame, header_style=None, cell_style=None) -> OdfTable:
        """Convierte DataFrame a tabla ODF nativa."""
        table = OdfTable()

        # Columnas
        for col in df.columns:
            table.addElement(TableColumn())

        # Fila de cabecera
        header_row = TableRow()
        for col in df.columns:
            # Usar estilo de cabecera
            cell = TableCell(stylename=header_style)
            cell.addElement(P(text=str(col)))
            header_row.addElement(cell)
        table.addElement(header_row)

        # Filas de datos
        for _, row in df.iterrows():
            tr = TableRow()
            for val in row:
                # Usar estilo de celda normal
                cell = TableCell(stylename=cell_style)
                cell.addElement(P(text=str(val)))
                tr.addElement(cell)
            table.addElement(tr)

        return table

    def _apply_style_from_config(self, style: Style, config: Dict):
        """Aplica configuración de estilos al objeto Style."""
        text_props = {}
        para_props = {}
        cell_props = {}
        
        if 'color' in config:
            text_props['color'] = config['color']
        if 'size' in config:
            text_props['fontsize'] = f"{config['size']}pt"
        if 'bold' in config and config['bold']:
            text_props['fontweight'] = "bold"
        if 'italic' in config and config['italic']:
            text_props['fontstyle'] = "italic"
            
        if 'align' in config:
            para_props['textalign'] = config['align']
            
        if 'bg_color' in config:
            cell_props['backgroundcolor'] = config['bg_color']
        if 'border' in config:
            cell_props['border'] = config['border']
            
        if text_props:
            style.addElement(TextProperties(**text_props))
        if para_props:
            style.addElement(ParagraphProperties(**para_props))
        if cell_props:
            style.addElement(TableCellProperties(**cell_props))

    def export_html(self, context: Dict[str, Any], output_path: str):
        """
        Export only HTML (no PDF conversion).
        
        Args:
            context: Report data
            output_path: Path to save HTML file
        
        Returns:
            str: Path to HTML file
        """
        if self.backend != "html":
            raise ValueError("export_html() only works with backend='html'")
        
        if not self.env:
             raise ValueError("HTML backend not initialized correctly (templates dir not found).")

        html_content = self._render_html_template(context)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html_content, encoding='utf-8')
        
        logger.info(f"HTML exported to {output}")
        return str(output)

    # Legacy method for backward compatibility
    @staticmethod
    def dataframe_to_html(df, classes: str = "table table-striped") -> str:
        """
        DEPRECATED: Legacy method for WeasyPrint compatibility.
        Use generate_pdf() with table_data instead.
        """
        logger.warning("dataframe_to_html() is deprecated. Use generate_pdf() with table_data")
        return df.to_html(classes=classes, index=False)
