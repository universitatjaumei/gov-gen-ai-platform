"""Sembrado de primera instalación (11.3).

Crea lo mínimo para que una instalación recién migrada sea usable:
SuperAdmin, una organización, una configuración de LLM, un chatbot de ejemplo y
sus prompts de bienvenida en castellano, catalán e inglés.

**Idempotente**: cada entidad se busca por su clave natural antes de crearse, así
que ejecutarlo dos veces no duplica nada ni pisa lo que el administrador haya
cambiado después (en particular, no rehashea la contraseña del SuperAdmin).

Ejecutar con:
    uv run python -m server.app.scripts.bootstrap --superadmin-email ... --superadmin-password ...

Lo invoca `scripts/setup.sh`; también sirve suelto para reparar una instalación.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid

from sqlalchemy import select

from server.app.core.security import hash_password
from server.app.database.models import SuperAdminAccount
from server.app.modules.agents_hub.database.config_models import (
    HubChatbot,
    HubLLMConfig,
    HubOrganizacion,
    HubProvider,
    HubPromptTemplate,
)
from server.app.modules.agents_hub.database.connection import (
    create_async_engine,
    create_session_factory,
)

# Claves naturales del sembrado. Cambiarlas rompe la idempotencia sobre
# instalaciones ya sembradas: crearía un segundo juego de entidades.
ORGANIZACION_NOMBRE = "Organización de ejemplo"
ORGANIZACION_PARTNER_ID = "govgenai-bootstrap"
CHATBOT_NOMBRE = "Chatbot de Ejemplo"
PROVIDER_ID = "ollama"
PROMPT_SLUG = "system_base"

SYSTEM_PROMPT = (
    "Eres el asistente de ejemplo de Gov Gen AI Platform. Responde siempre a "
    "partir de la documentación recuperada y cita tus fuentes. Si no encuentras "
    "información suficiente, dilo con claridad en lugar de improvisar."
)

PROMPTS_BIENVENIDA = {
    "es": (
        "Te damos la bienvenida. Soy el asistente de ejemplo de la plataforma. "
        "Puedo responder preguntas sobre la documentación que se haya cargado en "
        "mi base de conocimiento, indicando siempre de qué documento procede cada "
        "respuesta. Si no dispongo de información suficiente, te lo diré."
    ),
    "ca": (
        "Et donem la benvinguda. Soc l'assistent d'exemple de la plataforma. "
        "Puc respondre preguntes sobre la documentació que s'hagi carregat a la "
        "meva base de coneixement, indicant sempre de quin document prové cada "
        "resposta. Si no tinc prou informació, t'ho diré."
    ),
    "en": (
        "Welcome. I am the platform's example assistant. I can answer questions "
        "about the documentation loaded into my knowledge base, always stating "
        "which document each answer comes from. If I do not have enough "
        "information, I will say so."
    ),
}


class _Informe:
    """Lleva la cuenta de qué se creó y qué ya estaba, para el resumen final."""

    def __init__(self) -> None:
        self.creado: list[str] = []
        self.existente: list[str] = []

    def registrar(self, etiqueta: str, se_creo: bool) -> None:
        (self.creado if se_creo else self.existente).append(etiqueta)

    def imprimir(self) -> None:
        for etiqueta in self.creado:
            print(f"  [creado]      {etiqueta}")
        for etiqueta in self.existente:
            print(f"  [ya existía]  {etiqueta}")
        if not self.creado:
            print("\nNada que hacer: la instalación ya estaba sembrada.")


async def _sembrar(email: str, password: str, nombre: str, url: str | None) -> _Informe:
    informe = _Informe()
    engine = create_async_engine(url)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            # --- SuperAdmin ------------------------------------------------
            existente = (
                await session.execute(
                    select(SuperAdminAccount).where(SuperAdminAccount.email == email)
                )
            ).scalar_one_or_none()

            if existente is None:
                session.add(
                    SuperAdminAccount(
                        name=nombre,
                        email=email,
                        hashed_password=hash_password(password),
                        is_active=True,
                    )
                )
                informe.registrar(f"SuperAdmin {email}", True)
            else:
                # No se rehashea ni se pisa: si el admin cambió la contraseña
                # después de instalar, reejecutar setup.sh no debe revertirla.
                informe.registrar(f"SuperAdmin {email}", False)

            # --- Proveedor y configuración de LLM ---------------------------
            provider = await session.get(HubProvider, PROVIDER_ID)
            if provider is None:
                provider = HubProvider(
                    id=PROVIDER_ID,
                    name="Ollama (local)",
                    provider_type="openai_compatible",
                    base_url="http://ollama:11434/v1",
                )
                session.add(provider)
                informe.registrar(f"Proveedor '{PROVIDER_ID}'", True)
            else:
                informe.registrar(f"Proveedor '{PROVIDER_ID}'", False)

            llm_config = (
                await session.execute(
                    select(HubLLMConfig).where(HubLLMConfig.provider == PROVIDER_ID)
                )
            ).scalars().first()

            if llm_config is None:
                llm_config = HubLLMConfig(
                    id=uuid.uuid4(),
                    provider=PROVIDER_ID,
                    model_name="llama3.1:8b",
                    label="Modelo local por defecto",
                    tier=1,
                    is_default=True,
                )
                session.add(llm_config)
                informe.registrar("Configuración de LLM por defecto", True)
            else:
                informe.registrar("Configuración de LLM por defecto", False)

            # --- Organización ------------------------------------------------
            organizacion = (
                await session.execute(
                    select(HubOrganizacion).where(
                        HubOrganizacion.name == ORGANIZACION_NOMBRE
                    )
                )
            ).scalar_one_or_none()

            if organizacion is None:
                organizacion = HubOrganizacion(
                    id=uuid.uuid4(),
                    name=ORGANIZACION_NOMBRE,
                    partner_id=ORGANIZACION_PARTNER_ID,
                )
                session.add(organizacion)
                informe.registrar(f"Organización '{ORGANIZACION_NOMBRE}'", True)
            else:
                informe.registrar(f"Organización '{ORGANIZACION_NOMBRE}'", False)

            # Necesario para disponer de los ids antes de referenciarlos.
            await session.flush()

            # --- Chatbot de ejemplo ------------------------------------------
            chatbot = (
                await session.execute(
                    select(HubChatbot).where(HubChatbot.name == CHATBOT_NOMBRE)
                )
            ).scalar_one_or_none()

            if chatbot is None:
                chatbot = HubChatbot(
                    id=uuid.uuid4(),
                    organizacion_id=organizacion.id,
                    llm_config_id=llm_config.id,
                    name=CHATBOT_NOMBRE,
                    system_prompt=SYSTEM_PROMPT,
                )
                session.add(chatbot)
                await session.flush()
                informe.registrar(f"Chatbot '{CHATBOT_NOMBRE}'", True)
            else:
                informe.registrar(f"Chatbot '{CHATBOT_NOMBRE}'", False)

            # --- Prompts de bienvenida (es, ca, en) ---------------------------
            for idioma, texto in PROMPTS_BIENVENIDA.items():
                existente_prompt = (
                    await session.execute(
                        select(HubPromptTemplate).where(
                            HubPromptTemplate.chatbot_id == chatbot.id,
                            HubPromptTemplate.slug == PROMPT_SLUG,
                            HubPromptTemplate.language == idioma,
                        )
                    )
                ).scalar_one_or_none()

                if existente_prompt is None:
                    session.add(
                        HubPromptTemplate(
                            id=uuid.uuid4(),
                            chatbot_id=chatbot.id,
                            slug=PROMPT_SLUG,
                            language=idioma,
                            template_text=texto,
                        )
                    )
                    informe.registrar(f"Prompt de bienvenida [{idioma}]", True)
                else:
                    informe.registrar(f"Prompt de bienvenida [{idioma}]", False)

            await session.commit()
    finally:
        await engine.dispose()

    return informe


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m server.app.scripts.bootstrap",
        description="Sembrado idempotente de primera instalación.",
    )
    parser.add_argument("--superadmin-email", default=os.environ.get("SUPERADMIN_EMAIL", ""))
    parser.add_argument(
        "--superadmin-password", default=os.environ.get("SUPERADMIN_PASSWORD", "")
    )
    parser.add_argument(
        "--superadmin-name", default=os.environ.get("SUPERADMIN_NAME", "Superadministrador")
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Por defecto, DATABASE_URL del entorno.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    faltan = [
        nombre
        for nombre, valor in (
            ("--superadmin-email", args.superadmin_email),
            ("--superadmin-password", args.superadmin_password),
        )
        if not valor
    ]
    if faltan:
        print(f"ERROR: faltan argumentos obligatorios: {', '.join(faltan)}", file=sys.stderr)
        return 2

    print("Sembrando la instalación...")
    informe = asyncio.run(
        _sembrar(
            email=args.superadmin_email,
            password=args.superadmin_password,
            nombre=args.superadmin_name,
            url=args.database_url,
        )
    )
    informe.imprimir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
