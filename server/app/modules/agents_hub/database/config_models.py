"""Modelos ORM de configuración para agents_hub."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.app.modules.agents_hub.database.base import HubConfigBase


class HubProvider(HubConfigBase):
    """Proveedor dinámico de LLMs (Google, OpenRouter, LMStudio, etc.)."""

    __tablename__ = "hub_providers"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. google, openrouter, lmstudio
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # openai_compatible, google_genai, etc
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    llm_configs: Mapped[list["HubLLMConfig"]] = relationship(back_populates="provider_rel")


class HubLLMConfig(HubConfigBase):
    """Configuración de modelo LLM reutilizable por chatbot."""

    __tablename__ = "hub_llm_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(
        String(50), ForeignKey("hub_providers.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.1)
    top_p: Mapped[float] = mapped_column(default=1.0)
    max_tokens: Mapped[int] = mapped_column(Integer, default=12000)
    api_key_secret_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chatbots: Mapped[list["HubChatbot"]] = relationship(back_populates="llm_config")
    provider_rel: Mapped["HubProvider"] = relationship(back_populates="llm_configs")


class HubOrganizacion(HubConfigBase):
    """Institución (organización) gestionada por un admin."""

    __tablename__ = "hub_organizaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    theme_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # --- Defaults del grafo público (cascada hacia chatbots) ---
    default_public_graph_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="PUBLIC_KB_RICH")
    default_retrieval_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="RAG")
    default_language_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="prefer")
    default_quality_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    default_min_retrieval_results: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    default_min_retrieval_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    default_reranker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_answer_template: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    # Nullable a propósito, al revés que sus hermanas: NULL significa «heredar el default
    # de plataforma» (VIS.2). Con un valor no nulo por defecto, subir el presupuesto en la
    # plataforma no llegaría nunca a las organizaciones ya creadas.
    default_context_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chatbots: Mapped[list["HubChatbot"]] = relationship(
        back_populates="organizacion", cascade="all, delete-orphan"
    )


class HubVocabularyTerm(HubConfigBase):
    """Término del vocabulario controlado del corpus (ING.0.1).

    Deploy: cloud — es configuración institucional y se sincroniza cloud→edge.
    Los módulos edge NO importan este modelo: leen vía `ConfigProvider.list_vocabulary`.

    **No lleva CheckConstraint sobre `codi` ni sobre `axis`, y es deliberado**: el
    vocabulario de ámbitos y submaterias está pendiente de validación por Secretaría
    General y tiene que poder cambiar sin migración. Un CHECK sería exactamente lo que
    lo impide (CLAUDE.md §5).

    Renombrar o fusionar un término = fila nueva + la vieja con `vigent=False` y
    `substituit_per_codi` apuntando a la nueva. **La cadena de sustituciones ES la
    traza de auditoría**: no hay tabla de historial aparte.
    """

    __tablename__ = "hub_vocabulary_terms"
    __table_args__ = (
        UniqueConstraint(
            "organizacion_id", "axis", "codi", name="uq_vocabulary_org_axis_codi"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organizacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    axis: Mapped[str] = mapped_column(String(20), nullable=False)
    codi: Mapped[str] = mapped_column(String(80), nullable=False)
    nom_primari: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_secundari: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_codi: Mapped[str | None] = mapped_column(String(80), nullable=True)
    descripcio_router: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordre: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vigent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    substituit_per_codi: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubChatbot(HubConfigBase):
    """Chatbot RAG asociado a una organización."""

    __tablename__ = "hub_chatbots"
    __table_args__ = (
        CheckConstraint(
            "retrieval_mode IN ('RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR')",
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
    organizacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_organizaciones.id", ondelete="CASCADE"),
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
    retrieval_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="RAG")
    retrieval_top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    use_prompt_caching: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="atomic")
    # --- Campos del grafo público (9B.2) ---
    public_graph_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="PUBLIC_KB_RICH")
    language_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="prefer")
    quality_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    min_retrieval_results: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    min_retrieval_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reranker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    answer_template: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    # Presupuesto de contexto en tokens para la inyección de documentos (VIS.2). NULL =
    # heredar de la organización y, en su defecto, del default de plataforma. Lo consume
    # LongContextRetrievalStrategy para RECORTAR, no para lanzar una excepción.
    context_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

    organizacion: Mapped["HubOrganizacion"] = relationship(back_populates="chatbots")
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


class HubSsoUser(HubConfigBase):
    """Usuario aprovisionado vía SSO SAML (AUTH.2).

    Identidades que llegan por el IdP institucional y no son SuperAdminAccount ni
    AdminAccount. Se crea/actualiza Just-In-Time tras validar la aserción.
    """

    __tablename__ = "hub_sso_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="user")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # NameID
    idp_entity_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HubPersonalAccessToken(HubConfigBase):
    """Personal Access Token revocable para clientes máquina (AUTH.3).

    Se guarda solo el hash sha256 del token y un prefijo visible para identificarlo
    en la UI; el texto plano se entrega una única vez en la creación.
    """

    __tablename__ = "hub_personal_access_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(320), nullable=False)
    owner_role: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_prefix: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
