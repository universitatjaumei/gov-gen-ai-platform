"""Modelos ORM de configuración para agents_hub."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.app.modules.agents_hub.database.base import HubConfigBase


class HubLLMConfig(HubConfigBase):
    """Configuración de modelo LLM reutilizable por chatbot."""

    __tablename__ = "hub_llm_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # google | openai | ollama
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    api_key_secret_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chatbots: Mapped[list["HubChatbot"]] = relationship(back_populates="llm_config")


class HubClient(HubConfigBase):
    """Institución (cliente) gestionada por un partner."""

    __tablename__ = "hub_clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chatbots: Mapped[list["HubChatbot"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class HubChatbot(HubConfigBase):
    """Chatbot RAG asociado a un cliente."""

    __tablename__ = "hub_chatbots"
    __table_args__ = (
        CheckConstraint(
            "retrieval_mode IN ('vector', 'long_context', 'agentic')",
            name="ck_chatbot_retrieval_mode",
        ),
        CheckConstraint(
            "kind IN ('atomic', 'router')",
            name="ck_chatbot_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    llm_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_llm_configs.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    retrieval_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="vector")
    retrieval_top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="atomic")
    parent_chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_chatbots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    client: Mapped["HubClient"] = relationship(back_populates="chatbots")
    llm_config: Mapped["HubLLMConfig"] = relationship(back_populates="chatbots")
    prompt_templates: Mapped[list["HubPromptTemplate"]] = relationship(
        back_populates="chatbot", cascade="all, delete-orphan"
    )


class HubPromptTemplate(HubConfigBase):
    """Prompt parametrizable por chatbot, slug e idioma."""

    __tablename__ = "hub_prompt_templates"
    __table_args__ = (
        UniqueConstraint(
            "chatbot_id", "slug", "language", name="uq_prompt_chatbot_slug_lang"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)  # ej: system_base
    language: Mapped[str] = mapped_column(String(10), nullable=False)  # ca | es | en
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    default_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chatbot: Mapped["HubChatbot"] = relationship(back_populates="prompt_templates")
