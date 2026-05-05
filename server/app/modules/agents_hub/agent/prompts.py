"""Plantillas de system prompt para el grafo del agente."""

CITATION_RULES = """\
REGLAS DE CITA (obligatorias):
1. Cada afirmacion factual basada en los documentos debe ir seguida de una cita en formato
   markdown `[titulo del documento](url)`. La cita va al final de la frase citada.
2. Si una afirmacion combina varios documentos, cita todos: `[doc1](url1) [doc2](url2)`.
3. Si la pregunta no puede responderse con la informacion disponible, dilo explicitamente:
   "No tengo informacion suficiente en los documentos disponibles para responder a esta
   pregunta con citas verificables." NO inventes informacion ni cites documentos no
   recuperados.
4. NUNCA inventes URLs ni titulos. Usa SOLO los proporcionados en el contexto."""


def build_system_prompt(
    base_prompt: str,
    language: str,
    sources_block: str,
    mode: str,
) -> str:
    """Construye el system prompt final.

    Args:
        base_prompt: system_prompt definido por el admin para el chatbot.
        language: idioma de respuesta detectado.
        sources_block: bloque markdown con los documentos (vacio en agentic).
        mode: vector | long_context | agentic.
    """
    parts = [base_prompt.strip(), "", f"Responde en {language}.", "", CITATION_RULES.strip()]
    if mode == "MD_AGENT_SELECTOR":
        parts.append(
            "\nUsa la tool `list_documents` para ver el indice y `read_document(id=...)` "
            "para cargar el texto completo de cada documento que necesites antes de responder."
        )
    elif sources_block:
        parts.extend(["", "DOCUMENTOS DISPONIBLES:", "", sources_block])
    return "\n".join(parts)


def format_sources_block(sources: list) -> str:
    """Convierte Source[] en un bloque markdown que el LLM puede leer y citar."""
    if not sources:
        return ""
    lines = []
    for s in sources:
        lines.append(f"## {s.title}")
        lines.append(f"_URL: {s.url}_")
        lines.append("")
        lines.append(s.excerpt)
        lines.append("")
    return "\n".join(lines)
