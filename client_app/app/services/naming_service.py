"""
Naming Service - Generación de nombres provisionales para átomos y flujos.

Este servicio implementa la lógica de "Naming Silencioso" para evitar la
"parálisis de la hoja en blanco" al crear nuevos recursos.
"""

from typing import List, Optional, Dict, Any
from automatia_shared.enums import StepType


# Mapeo de StepType a nombres legibles
TYPE_NAMES = {
    StepType.EXTRACTION: "Extracción",
    StepType.ETL: "Procesado",
    StepType.ETL_TRANSFORM: "Transformación",
    StepType.RPA_EXECUTE: "Automatización",
    StepType.CUSTOM_SCRIPT: "Script",
    StepType.API_FETCH: "API",
    StepType.SQL_QUERY: "Consulta SQL",
    StepType.EMAIL: "Email",
    StepType.EMAIL_SEND: "Envío Email",
    StepType.EMAIL_WATCHER: "Monitor Email",
    StepType.FOLDER_WATCHER: "Monitor Carpeta",
    StepType.SMTP: "SMTP",
    StepType.REPORT_GENERATE: "Informe",
    StepType.ANONYMIZATION: "Anonimización",
    StepType.MASKING: "Enmascarado",
    StepType.CONNECTION: "Conexión",
    StepType.NAVIGATION: "Navegación",
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.SCHEDULER: "Programador",
    StepType.FOLDER_SCAN: "Escaneo Carpeta",
    StepType.EMAIL_SCAN: "Escaneo Email",
    StepType.ARCHIVE_FILE: "Archivado",
    StepType.GRAPHICS: "Gráficos",
    StepType.LLM_PROCESS: "Procesamiento LLM",
}

# Símbolos cortos para cadenas de flujo
TYPE_SYMBOLS = {
    StepType.EXTRACTION: "PDF",
    StepType.ETL: "ETL",
    StepType.ETL_TRANSFORM: "ETL",
    StepType.RPA_EXECUTE: "RPA",
    StepType.CUSTOM_SCRIPT: "Script",
    StepType.API_FETCH: "API",
    StepType.SQL_QUERY: "SQL",
    StepType.EMAIL: "Email",
    StepType.EMAIL_SEND: "Email",
    StepType.EMAIL_WATCHER: "Email",
    StepType.FOLDER_WATCHER: "Folder",
    StepType.SMTP: "SMTP",
    StepType.REPORT_GENERATE: "Report",
    StepType.ANONYMIZATION: "Anon",
    StepType.MASKING: "Mask",
    StepType.CONNECTION: "Conn",
    StepType.NAVIGATION: "Nav",
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.SCHEDULER: "Sched",
    StepType.FOLDER_SCAN: "Scan",
    StepType.EMAIL_SCAN: "Email",
    StepType.ARCHIVE_FILE: "Archive",
    StepType.GRAPHICS: "Chart",
    StepType.LLM_PROCESS: "LLM",
}


def generate_provisional_name(step_type: StepType, config: Optional[Dict[str, Any]] = None, index: int = 1) -> str:
    """
    Genera un nombre provisional basado en el tipo y configuración del átomo.

    Args:
        step_type: Tipo del paso/átomo
        config: Configuración del átomo (opcional)
        index: Índice numérico para diferenciar múltiples átomos del mismo tipo

    Returns:
        Nombre provisional (ej: "Extracción #1", "API: Clientes")
    """
    base_name = TYPE_NAMES.get(step_type, "Paso")

    # Intentar extraer contexto de la configuración
    if config:
        # Para conexiones API con nombre de endpoint
        if step_type == StepType.API_FETCH:
            endpoint = config.get('endpoint_name') or config.get('name')
            if endpoint:
                return f"API: {endpoint[:30]}"

        # Para SQL con nombre de conexión
        if step_type == StepType.SQL_QUERY:
            conn_name = config.get('connection_name') or config.get('name')
            if conn_name:
                return f"SQL: {conn_name[:30]}"

        # Para watchers con ruta/email
        if step_type == StepType.FOLDER_WATCHER:
            path = config.get('watch_path') or config.get('path')
            if path:
                folder_name = path.split('/')[-1] or path.split('\\')[-1]
                return f"Carpeta: {folder_name[:25]}"

        if step_type == StepType.EMAIL_WATCHER:
            email = config.get('email_address') or config.get('email')
            if email:
                return f"Email: {email[:25]}"

        # Para RPA con URL
        if step_type == StepType.RPA_EXECUTE:
            url = config.get('url') or config.get('target_url')
            if url:
                # Extraer dominio
                domain = url.replace('https://', '').replace('http://', '').split('/')[0]
                return f"RPA: {domain[:25]}"

        # --- Nuevos tipos de la taxonomía v2 ---
        if step_type == StepType.SCHEDULER:
            flow_name = config.get('flow_name', '')
            if flow_name:
                return f"Programar: {flow_name[:25]}"

        if step_type == StepType.FOLDER_SCAN:
            path = config.get('scan_path') or config.get('path')
            if path:
                folder_name = path.split('/')[-1] or path.split('\\')[-1]
                return f"Escaneo: {folder_name[:20]}"

        if step_type == StepType.EMAIL_SCAN:
            subject = config.get('subject_contains')
            if subject:
                return f"Emails: {subject[:20]}"

        if step_type == StepType.ARCHIVE_FILE:
            dest = config.get('destination_path') or config.get('destination')
            if dest:
                folder_name = dest.split('/')[-1] or dest.split('\\')[-1]
                return f"Archivar: {folder_name[:20]}"

        if step_type == StepType.GRAPHICS:
            chart_type = config.get('chart_type')
            if chart_type:
                return f"Gráfico: {chart_type[:20]}"

        if step_type == StepType.LLM_PROCESS:
            instruction = config.get('instruction') or config.get('user_prompt', '')
            if instruction:
                # Extraer primeras palabras significativas
                preview = instruction[:35].strip()
                return f"LLM: {preview}..."

    return f"{base_name} #{index}"


def generate_provisional_description(step_type: StepType, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Genera una descripción técnica basada en la configuración del átomo.

    Args:
        step_type: Tipo del paso/átomo
        config: Configuración del átomo (opcional)

    Returns:
        Descripción técnica provisional
    """
    if not config:
        return f"Configuración de {TYPE_NAMES.get(step_type, 'paso')}"

    # Descripciones específicas por tipo
    if step_type == StepType.RPA_EXECUTE:
        url = config.get('url') or config.get('target_url', '')
        if url:
            return f"Automatización en {url}"
        return "Automatización web"

    if step_type == StepType.EXTRACTION:
        fields = config.get('fields') or config.get('extracted_fields', [])
        if fields:
            field_names = [f.get('name', f) if isinstance(f, dict) else str(f) for f in fields[:3]]
            return f"Extracción de {', '.join(field_names)}"
        return "Extracción de datos de documento"

    if step_type == StepType.ETL or step_type == StepType.ETL_TRANSFORM:
        file_type = config.get('file_type') or config.get('input_format', '')
        if file_type:
            return f"Procesado de {file_type.upper()}"
        return "Transformación de datos"

    if step_type == StepType.API_FETCH:
        method = config.get('method', 'GET')
        endpoint = config.get('endpoint_url') or config.get('url', '')
        if endpoint:
            return f"{method} a {endpoint[:50]}"
        return "Consulta a API externa"

    if step_type == StepType.SQL_QUERY:
        conn_name = config.get('connection_name', '')
        if conn_name:
            return f"Consulta SQL en {conn_name}"
        return "Consulta a base de datos"

    if step_type == StepType.FOLDER_WATCHER:
        path = config.get('watch_path') or config.get('path', '')
        if path:
            return f"Monitoreo de carpeta: {path}"
        return "Monitoreo de sistema de archivos"

    if step_type == StepType.EMAIL_WATCHER:
        email = config.get('email_address') or config.get('email', '')
        if email:
            return f"Monitoreo de bandeja: {email}"
        return "Monitoreo de correo entrante"

    if step_type == StepType.REPORT_GENERATE:
        template = config.get('template_name') or config.get('template', '')
        if template:
            return f"Generación de informe: {template}"
        return "Generación de informe"

    if step_type == StepType.ANONYMIZATION:
        return "Anonimización de datos sensibles"

    if step_type == StepType.SMTP:
        return "Envío de correo electrónico"

    # --- Nuevos tipos de la taxonomía v2 ---
    if step_type == StepType.SCHEDULER:
        schedule_type = config.get('schedule_type', '')
        if schedule_type:
            return f"Programación {schedule_type}"
        return "Programación de ejecución de flujo"

    if step_type == StepType.FOLDER_SCAN:
        path = config.get('scan_path') or config.get('path', '')
        pattern = config.get('pattern', '*')
        if path:
            folder_name = path.split('/')[-1] or path.split('\\')[-1] or path
            return f"Escaneo de {folder_name} ({pattern})"
        return "Escaneo de carpeta por patrón"

    if step_type == StepType.EMAIL_SCAN:
        subject = config.get('subject_contains', '')
        if subject:
            return f"Búsqueda de emails: '{subject[:30]}'"
        return "Búsqueda de emails por criterio"

    if step_type == StepType.ARCHIVE_FILE:
        dest = config.get('destination_path') or config.get('destination', '')
        if dest:
            folder_name = dest.split('/')[-1] or dest.split('\\')[-1] or dest
            return f"Archivado en {folder_name}"
        return "Archivado de resultados"

    if step_type == StepType.GRAPHICS:
        chart_type = config.get('chart_type', '')
        if chart_type:
            return f"Gráfico de tipo {chart_type}"
        return "Generación de gráficos"

    if step_type == StepType.LLM_PROCESS:
        instruction = config.get('instruction') or config.get('user_prompt', '')
        if instruction:
            return f"Procesamiento LLM: {instruction[:40]}..."
        return "Procesamiento de texto con IA generativa"

    return f"Configuración de {TYPE_NAMES.get(step_type, 'paso')}"


def generate_flow_name(steps: List[Any]) -> str:
    """
    Genera nombre de flujo concatenando tipos de pasos.

    Args:
        steps: Lista de pasos del flujo (deben tener atributo 'type' o 'step_type')

    Returns:
        Nombre de flujo (ej: "PDF → ETL → Excel")
    """
    if not steps:
        return "Nuevo Flujo"

    chain = []
    for step in steps[:5]:  # Máximo 5 símbolos
        # Obtener el tipo del paso
        step_type = getattr(step, 'type', None) or getattr(step, 'step_type', None)
        if isinstance(step, dict):
            step_type = step.get('type') or step.get('step_type')

        # Convertir string a enum si es necesario
        if isinstance(step_type, str):
            try:
                step_type = StepType(step_type)
            except ValueError:
                step_type = None

        symbol = TYPE_SYMBOLS.get(step_type, "?")
        chain.append(symbol)

    return " → ".join(chain)


def generate_flow_description(steps: List[Any]) -> str:
    """
    Genera descripción resumida del flujo basada en sus pasos.

    Args:
        steps: Lista de pasos del flujo

    Returns:
        Descripción del flujo
    """
    if not steps:
        return ""

    chain_name = generate_flow_name(steps)
    return f"Flujo de {len(steps)} paso{'s' if len(steps) > 1 else ''}: {chain_name}"


# Instancia singleton para uso consistente
class NamingService:
    """Servicio de naming para uso consistente en toda la aplicación."""

    @staticmethod
    def provisional_name(step_type: StepType, config: Optional[Dict[str, Any]] = None, index: int = 1) -> str:
        return generate_provisional_name(step_type, config, index)

    @staticmethod
    def generate_provisional_name(step_type: StepType, config: Optional[Dict[str, Any]] = None, index: int = 1) -> str:
        """Alias for provisional_name to maintain compatibility."""
        return generate_provisional_name(step_type, config, index)

    @staticmethod
    def provisional_description(step_type: StepType, config: Optional[Dict[str, Any]] = None) -> str:
        return generate_provisional_description(step_type, config)

    @staticmethod
    def generate_provisional_description(step_type: StepType, config: Optional[Dict[str, Any]] = None) -> str:
        """Alias for provisional_description to maintain compatibility."""
        return generate_provisional_description(step_type, config)

    @staticmethod
    def flow_name(steps: List[Any]) -> str:
        return generate_flow_name(steps)

    @staticmethod
    def flow_description(steps: List[Any]) -> str:
        return generate_flow_description(steps)


naming_service = NamingService()
