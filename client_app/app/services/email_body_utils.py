"""
Utilidades para extracción y limpieza del cuerpo de emails.

Este módulo centraliza la lógica de procesamiento de contenido de emails
para uso compartido entre EmailScanService y EmailWatcher.
"""
import re
import email
from email.message import Message
from typing import Optional, Tuple
from html import unescape


def extract_email_body(msg: Message) -> Tuple[str, Optional[str]]:
    """
    Extrae el cuerpo del email (texto plano y HTML).

    Args:
        msg: Objeto email.message.Message parseado

    Returns:
        Tupla (body_text, body_html) donde body_html puede ser None
    """
    body_text = ""
    body_html = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Saltar adjuntos
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")

            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_html = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            content = payload.decode(charset, errors="replace")

            # Determinar si es HTML o texto plano
            if msg.get_content_type() == "text/html":
                body_html = content
                body_text = strip_html_tags(content)
            else:
                body_text = content

    return body_text, body_html


def strip_html_tags(html: str) -> str:
    """
    Elimina etiquetas HTML y devuelve texto plano limpio.

    Args:
        html: Contenido HTML

    Returns:
        Texto plano sin etiquetas
    """
    if not html:
        return ""

    # Eliminar scripts y styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Convertir <br> y </p> a saltos de línea
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div\s*>', '\n', text, flags=re.IGNORECASE)

    # Eliminar todas las etiquetas HTML restantes
    text = re.sub(r'<[^>]+>', '', text)

    # Decodificar entidades HTML
    text = unescape(text)

    # Limpiar espacios excesivos
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()


def clean_email_body(body: str) -> str:
    """
    Limpia el cuerpo del email eliminando firmas y colapsando hilos.

    Operaciones:
    - Elimina firmas comunes (después de --, Saludos, Best regards, etc.)
    - Colapsa hilos de respuesta (queda solo el mensaje más reciente)
    - Elimina líneas de citado repetidas

    Args:
        body: Texto plano del cuerpo del email

    Returns:
        Texto limpio optimizado para consumo por LLM
    """
    if not body:
        return ""

    lines = body.split('\n')
    cleaned_lines = []

    # Patrones de firma
    signature_patterns = [
        r'^--\s*$',  # Separador estándar de firma
        r'^_{3,}$',  # Línea de guiones bajos
        r'^-{3,}$',  # Línea de guiones
        r'^Saludos\s*[,.]?\s*$',
        r'^Saludos cordiales\s*[,.]?\s*$',
        r'^Atentamente\s*[,.]?\s*$',
        r'^Cordialmente\s*[,.]?\s*$',
        r'^Un saludo\s*[,.]?\s*$',
        r'^Best regards\s*[,.]?\s*$',
        r'^Kind regards\s*[,.]?\s*$',
        r'^Regards\s*[,.]?\s*$',
        r'^Thanks\s*[,.]?\s*$',
        r'^Thank you\s*[,.]?\s*$',
        r'^Cheers\s*[,.]?\s*$',
        r'^Sent from my iPhone',
        r'^Sent from my Android',
        r'^Enviado desde mi',
    ]

    # Patrones de inicio de hilo citado
    quote_start_patterns = [
        r'^On .+ wrote:$',
        r'^El .+ escribió:$',
        r'^De: .+$',
        r'^From: .+$',
        r'^Enviado: .+$',
        r'^Sent: .+$',
        r'^-{2,}\s*Original Message\s*-{2,}',
        r'^-{2,}\s*Mensaje original\s*-{2,}',
        r'^>{2,}',  # Múltiples símbolos de citado
    ]

    in_signature = False
    in_quoted_thread = False

    for line in lines:
        stripped = line.strip()

        # Detectar inicio de firma
        if not in_signature:
            for pattern in signature_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    in_signature = True
                    break

        # Detectar inicio de hilo citado
        if not in_quoted_thread:
            for pattern in quote_start_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    in_quoted_thread = True
                    break

        # Saltar líneas de firma o hilos citados
        if in_signature or in_quoted_thread:
            continue

        # Saltar líneas que son solo citado (empiezan con >)
        if stripped.startswith('>'):
            continue

        cleaned_lines.append(line)

    # Unir y limpiar espacios excesivos
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def get_message_id(msg: Message) -> str:
    """
    Extrae el Message-ID del email para deduplicación.

    Args:
        msg: Objeto email.message.Message

    Returns:
        Message-ID o un ID generado basado en headers si no existe
    """
    message_id = msg.get("Message-ID", "")

    if message_id:
        # Limpiar el Message-ID (quitar < y >)
        message_id = message_id.strip("<>")
    else:
        # Generar un ID basado en otros headers
        import hashlib
        from_addr = msg.get("From", "")
        date = msg.get("Date", "")
        subject = msg.get("Subject", "")

        unique_string = f"{from_addr}|{date}|{subject}"
        message_id = hashlib.sha256(unique_string.encode()).hexdigest()[:32]

    return message_id


def build_llm_context(emails_data: list, max_chars: int = 50000) -> str:
    """
    Construye el contexto concatenado de múltiples emails para enviar a un LLM.

    Args:
        emails_data: Lista de dicts con 'sender', 'subject', 'date', 'body_plain'
        max_chars: Límite máximo de caracteres

    Returns:
        Texto formateado listo para usar como contexto de LLM
    """
    if not emails_data:
        return ""

    context_parts = []
    total_chars = 0

    for i, email_data in enumerate(emails_data, 1):
        sender = email_data.get('sender', 'Desconocido')
        subject = email_data.get('subject', 'Sin asunto')
        date = email_data.get('date', '')
        body = clean_email_body(email_data.get('body_plain', ''))

        # Formatear email
        email_block = f"""
--- Email {i} ---
De: {sender}
Asunto: {subject}
Fecha: {date}

{body}
"""

        # Verificar límite de caracteres
        if total_chars + len(email_block) > max_chars:
            context_parts.append("\n[... Correos adicionales omitidos por límite de tamaño ...]")
            break

        context_parts.append(email_block)
        total_chars += len(email_block)

    return "\n".join(context_parts).strip()
