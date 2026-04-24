"""Servicio de recuperación y formateo de prompts desde la base de datos."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.config_models import HubPromptTemplate


async def get_formatted_prompt(
    chatbot_id: uuid.UUID,
    slug: str,
    language: str,
    session: AsyncSession,
    **kwargs: str,
) -> str:
    """Recupera un template de prompt de la DB y aplica las variables.

    Args:
        chatbot_id: ID del chatbot
        slug: Identificador del template (ej: "system_base")
        language: Código de idioma (ca | es | en)
        session: Sesión de base de datos
        **kwargs: Variables a inyectar en el template

    Returns:
        Prompt formateado con las variables aplicadas

    Raises:
        KeyError: Si falta una variable requerida por el template
        ValueError: Si el template no existe
    """
    result = await session.execute(
        select(HubPromptTemplate).where(
            HubPromptTemplate.chatbot_id == chatbot_id,
            HubPromptTemplate.slug == slug,
            HubPromptTemplate.language == language,
        )
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise ValueError(
            f"Template '{slug}' para idioma '{language}' no encontrado en chatbot {chatbot_id}"
        )

    try:
        return template.template_text.format(**kwargs)
    except KeyError as e:
        # Variable inexistente: devolver template sin formatear para no romper el flujo
        return template.template_text
