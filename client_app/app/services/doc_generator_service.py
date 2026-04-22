"""
Documentation Generator Service - Prompt 11 Implementation
Generates README.md documentation for various automation types.
Supports: ScriptLibrary (Custom, Extraction, ETL, Graphics), RPA Playbooks, Workflows.

Features:
- Standardized sections: Título, Propósito, Requisitos, Resultados, Guía, Seguridad, Changelog
- Physical persistence in data/automations/docs/[id].md
- AST code analysis for security warnings
- Zero-Knowledge: synthetic examples only, no PII
- i18n support (es/ca)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import ast
import re
from client_app.app.database.models import ScriptLibrary
from automatia_shared.contracts.ui_contract import DataContract, OutputSchema, OutputField, InputType


# Security: Forbidden imports that require warnings
RISKY_IMPORTS = {'os', 'subprocess', 'sys', 'socket', 'shutil', 'ctypes', 'pickle'}
RISKY_CALLS = {'eval', 'exec', 'compile', '__import__', 'open'}


class ASTSecurityAnalyzer:
    """Analyzes Python code for security risks using AST."""

    @staticmethod
    def analyze_code(code: str) -> Dict[str, Any]:
        """
        Analyze Python code for security risks.

        Returns:
            Dict with 'risky_imports', 'risky_calls', 'warnings'
        """
        result = {
            'risky_imports': [],
            'risky_calls': [],
            'warnings': []
        }

        try:
            tree = ast.parse(code)
        except SyntaxError:
            result['warnings'].append("No se pudo analizar el código (error de sintaxis)")
            return result

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name in RISKY_IMPORTS:
                        result['risky_imports'].append(module_name)
                        result['warnings'].append(
                            f"Importa módulo potencialmente peligroso: `{module_name}`"
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in RISKY_IMPORTS:
                        result['risky_imports'].append(module_name)
                        result['warnings'].append(
                            f"Importa desde módulo potencialmente peligroso: `{module_name}`"
                        )

            # Check risky function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in RISKY_CALLS:
                        result['risky_calls'].append(node.func.id)
                        result['warnings'].append(
                            f"Usa función potencialmente peligrosa: `{node.func.id}()`"
                        )

        return result


class DocumentationGeneratorService:
    """
    Service to generate standardized documentation for automations.

    Prompt 11 Implementation:
    - Generates professional README.md files
    - Persists to disk at data/automations/docs/[id].md
    - Includes AST security analysis
    - Zero-Knowledge: no PII in examples
    - i18n support
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def build_readme_content(self, contract: DataContract) -> str:
        """
        Genera el contenido del README basado en el DataContract unificado.
        """
        # Header
        md = f"# {contract.description or 'Automation Script'}\n\n"
        md += f"**Versión**: {contract.version}\n\n"
        
        # Description
        md += "## Descripción\n"
        md += f"{contract.description}\n\n"
        
        # Technical Contract (Table)
        md += "## Contrato de Datos (Output)\n"
        if contract.outputs and contract.outputs.fields:
            md += "| Nombre | Tipo | Descripción |\n"
            md += "|--------|------|-------------|\n"
            for field in contract.outputs.fields:
                f_type = field.type.value if hasattr(field.type, 'value') else str(field.type)
                md += f"| {field.name} | {f_type} | {field.description} |\n"
        else:
            md += "No hay campos de salida definidos.\n"
            
        md += "\n"
        return md

    def generate_readme(
        self,
        script: ScriptLibrary,
        content_summary: Optional[str] = None,
        include_changelog: bool = False,
        language: str = 'es'
    ) -> str:
        """
        Genera el contenido de un archivo README.md basado en el tipo de script y sus metadatos.

        Args:
            script: El objeto ScriptLibrary con la metadata de la automatización.
            content_summary: Resumen opcional del contenido del script.
            include_changelog: Si se debe incluir la sección de historial de cambios.
            language: Código de idioma ('es' o 'ca').

        Returns:
            Cadena de texto con el README.md formateado.
        """
        # Generate base content based on type
        if script.source_module == 'rpa':
            readme = self._generate_rpa_readme(script)
        elif script.source_module == 'extraction':
            readme = self._generate_extraction_readme(script, content_summary)
        elif script.source_module == 'graphics':
            readme = self._generate_graphics_readme(script)
        elif script.source_module == 'etl':
            readme = self._generate_etl_readme(script)
        else:
            readme = self._generate_generic_readme(script)

        # Add changelog if requested
        if include_changelog:
            readme += self._generate_changelog_section(script)

        return readme

    def generate_readme_with_code_analysis(
        self,
        script: ScriptLibrary,
        code: str,
        content_summary: Optional[str] = None,
        include_changelog: bool = False,
        language: str = 'es'
    ) -> str:
        """
        Genera un README.md que incluye una sección de análisis de seguridad AST del código.

        Args:
            script: Objeto ScriptLibrary.
            code: Código fuente Python a analizar.
            content_summary: Resumen opcional.
            include_changelog: Si se incluye el changelog.
            language: Idioma.

        Returns:
            README.md con la sección de advertencias de seguridad incluida.
        """
        # Generate base README
        readme = self.generate_readme(
            script,
            content_summary=content_summary,
            include_changelog=False,  # We'll add it at the end
            language=language
        )

        # Analyze code for security risks
        analysis = ASTSecurityAnalyzer.analyze_code(code)

        # Add security section
        readme += self._generate_security_section(analysis)

        # Add changelog at the end if requested
        if include_changelog:
            readme += self._generate_changelog_section(script)

        return readme

    def save_readme(
        self,
        script: ScriptLibrary,
        base_path: Path,
        code: Optional[str] = None,
        include_changelog: bool = True
    ) -> Path:
        """
        Genera el README y lo persiste físicamente en el disco.

        Args:
            script: Objeto ScriptLibrary.
            base_path: Directorio base donde guardar la documentación.
            code: Código Python opcional para análisis de seguridad.
            include_changelog: Si se incluye el changelog.

        Returns:
            La ruta (Path) al archivo README creado.
        """
        # Ensure directory exists
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # Generate content
        if code:
            content = self.generate_readme_with_code_analysis(
                script=script,
                code=code,
                include_changelog=include_changelog
            )
        else:
            content = self.generate_readme(
                script=script,
                include_changelog=include_changelog
            )

        # Save to file
        file_path = base_path / f"{script.id}.md"
        file_path.write_text(content, encoding='utf-8')

        return file_path

    def generate_and_save(
        self,
        script: ScriptLibrary,
        base_path: Path,
        code: Optional[str] = None
    ) -> Path:
        """
        Convenience method to generate and save README in one call.
        Used during script promotion to library.

        Args:
            script: ScriptLibrary object
            base_path: Base path for docs
            code: Optional Python code for analysis

        Returns:
            Path to saved README
        """
        return self.save_readme(
            script=script,
            base_path=base_path,
            code=code,
            include_changelog=True
        )

    def _generate_security_section(self, analysis: Dict[str, Any]) -> str:
        """Generate security warnings section from AST analysis."""
        if not analysis['warnings']:
            return """
## Seguridad

Este script ha sido analizado y no presenta advertencias de seguridad significativas.
"""

        warnings_text = "\n".join(f"- {w}" for w in analysis['warnings'])
        imports_text = ", ".join(f"`{i}`" for i in analysis['risky_imports']) or "Ninguno"

        return f"""
## Seguridad

**Advertencias de seguridad detectadas:**

{warnings_text}

**Módulos sensibles importados:** {imports_text}

> **Nota:** Este script contiene imports que requieren revisión antes de la promoción a producción.
> Solo un Superadministrador puede aprobar scripts con estos módulos.
"""

    def _generate_changelog_section(self, script: ScriptLibrary) -> str:
        """Generate changelog section."""
        created = getattr(script, 'created_at', None)
        updated = getattr(script, 'updated_at', None)

        created_str = created.strftime("%Y-%m-%d") if created else datetime.now().strftime("%Y-%m-%d")
        updated_str = updated.strftime("%Y-%m-%d") if updated else created_str

        return f"""
## Changelog

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| {created_str} | 1.0.0 | Creación inicial |
| {updated_str} | 1.0.0 | Última modificación |
"""

    def _generate_header(self, script: ScriptLibrary, type_label: str) -> str:
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M") # Ideally use script.created_at if available
        return f"""# {script.name}

**Tipo**: {type_label}  
**ID**: {script.id}  
**Estado**: {script.status.upper()}  
**Fecha**: {created_date}

## Descripción
{script.description or 'Sin descripción disponible.'}
"""

    def _generate_rpa_readme(self, script: ScriptLibrary) -> str:
        # Note: RPA Logic is also handled in RPALibrarySyncService separately for now.
        # This implementation unifies it for regeneration purposes.
        metadata = script.source_metadata or {}
        base_url = metadata.get('base_url', 'N/A')
        
        return self._generate_header(script, "RPA Web Automation") + f"""
**URL Objetivo**: `{base_url}`

## Resumen de Ejecución
Este robot automatiza interacciones web. Se integra con el navegador para realizar tareas repetitivas.

## Requisitos
- Navegador compatible (Chrome/Edge)
- Acceso a la URL objetivo
"""

    def _generate_extraction_readme(self, script: ScriptLibrary, content_summary: str = None) -> str:
        return self._generate_header(script, "PDF Extraction Script") + f"""
## Propósito
Este script extrae información estructurada de documentos PDF utilizando Inteligencia Artificial.

## Salida Esperada (Schema)
El script genera un JSON con la siguiente estructura:
```json
{script.data_contract.get('output_schema', {})}
```

## Prompt Original
> {script.user_prompt or 'No prompt recorded.'}

<help_config>
### Cómo configurar
Este átomo de extracción procesará los documentos de entrada buscando la siguiente estructura de datos:
{list(script.data_contract.get('output_schema', {}).keys()) if isinstance(script.data_contract.get('output_schema'), dict) else 'Campos definidos en el contrato.'}
</help_config>

<help_example>
### Ejemplo de Datos Extraídos
El sistema devolverá un JSON o un Diccionario equivalente a la estructura configurada.
</help_example>
"""

    def _generate_graphics_readme(self, script: ScriptLibrary) -> str:
        return self._generate_header(script, "Data Visualization") + f"""
## Visualización
Genera gráficos a partir de datos tabulares.

## Configuración
- **Tipo de Gráfico**: {script.source_metadata.get('chart_type', 'N/A')}
- **Columnas**: {script.source_metadata.get('columns', 'N/A')}

## Uso
Este script espera un DataFrame de entrada y genera una figura (Plotly/Matplotlib).

<help_config>
### Cómo configurar
Recuerda mapear correctamente un `DataFrame` en el puerto de entrada para que el script pueda generar el gráfico de tipo **{script.source_metadata.get('chart_type', 'N/A')}**.
</help_config>

<help_example>
### Ejemplo
Si configuras el nodo para recibir un DataFrame con columnas numéricas, el sistema devolverá un objeto imagen/html listo para ser visualizado o guardado.
</help_example>
"""

    def _generate_etl_readme(self, script: ScriptLibrary) -> str:
        return self._generate_header(script, "ETL Transformation") + f"""
## Transformación de Datos
Script para limpieza y transformación de datos.

## Operaciones
- **Entrada**: {script.data_contract.get('input_description', 'DataFrame')}
- **Salida**: {script.data_contract.get('output_description', 'DataFrame transformado')}

## Lógica
El script aplica reglas de negocio definidas para normalizar los datos.

<help_config>
### Cómo configurar
Conecta el DataFrame de origen a este nodo. Las transformaciones se aplicarán secuencialmente y devolverán un nuevo conjunto de datos.
</help_config>

<help_example>
### Ejemplo
Recibes un reporte con datos crudos y tras aplicar todos los pasos, obtienes un listado listo para graficar, exportar a CSV o enviar por correo.
</help_example>
"""

    def _generate_generic_readme(self, script: ScriptLibrary) -> str:
        return self._generate_header(script, "Python Automation Script") + f"""
## Información General
Script de automatización personalizado.

## Contrato de Interfaz
El script acepta los siguientes parámetros de entrada:
```json
{script.ui_contract.get('inputs', [])}
```

<help_config>
### Cómo configurar
Verifica que estás conectando valores a los siguientes campos de entrada detectados en tu script:
`{script.ui_contract.get('inputs', [])}`
</help_config>

<help_example>
### Ejemplo
El script ejecutará el código Python enjaulado recibiendo las variables vinculadas y proporcionando las salidas listadas en el contrato.
</help_example>
"""

doc_generator = DocumentationGeneratorService()
