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
    """Configuración de un modelo reutilizable: chat, embeddings o reranking.

    `purpose` lo añade MOD.1 (ver `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`). Hasta
    entonces esta tabla era implícitamente de chat —lo delatan `temperature`, `top_p` y
    `max_tokens`—, y los modelos de embedding se elegían con un `import`, no con
    configuración. Con el propósito explícito se reutiliza todo lo que ya existe:
    proveedores con su `base_url` y su clave, `available-models` y el test de conexión.

    **Lleva CheckConstraint, al contrario que el vocabulario de ámbitos** (CLAUDE.md §5): son
    tres valores estables, cada uno con consumidor en el código, y añadir uno exige escribir
    el código que lo consuma. Mismo criterio que `nivell_acces` en ING.0.2.
    """

    __tablename__ = "hub_llm_configs"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('chat', 'embedding', 'rerank')",
            name="ck_llm_config_purpose",
        ),
    )

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
    # --- MOD.1: para qué sirve este modelo ---
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, default="chat")
    # Dimensión pedida al proveedor. None = la que dé por defecto. La plataforma trabaja a
    # 1024 porque es el único valor que sirve a la vez a BGE-M3 en edge (nativo) y a Google
    # en cloud (rango flexible 128-3072): mantenerlo salva la columna Vector(1024), el índice
    # HNSW y el corpus ya cargado cuando se cambia de proveedor.
    output_dimensionality: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    default_reranker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_answer_template: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    # Nullable a propósito, al revés que sus hermanas: NULL significa «heredar el default
    # de plataforma» (VIS.2). Con un valor no nulo por defecto, subir el presupuesto en la
    # plataforma no llegaría nunca a las organizaciones ya creadas.
    default_context_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- Troceado (RAG.8). Nullable = heredar del default de plataforma ---
    default_chunk_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_chunk_overlap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_chunking_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # --- Reescritura de consulta (RAG.10). NULL = heredar del default de plataforma ---
    # Nullable y no `default=False` como sus hermanas booleanas mas antiguas: con un False
    # no nulo, la organizacion pisaria siempre a la plataforma y encenderlo por organizacion
    # no serviria de nada. Es el mismo motivo por el que context_token_budget es nullable.
    default_query_rewriting_enabled: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    # Modelo con el que se reescribe: pequeno y rapido, distinto del que responde. Vive en
    # la organizacion porque repetirlo en cada chatbot solo multiplicaria sitios donde
    # olvidarlo. NULL = usar el del chatbot con el tope de salida bajado.
    rewrite_llm_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_llm_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # --- Cuotas de consumo (SEC.4). Todo en TOKENS ---
    #
    # `NULL` = heredar del nivel de arriba; `0` = **sin límite**. Son dos cosas distintas y
    # confundirlas es el fallo caro: si `0` significara «bloqueado», poner un límite a cero
    # para «quitar la restricción» dejaría al chatbot sin poder responder a nadie. Hay test.
    #
    # Los contadores NO viven aquí: son `HubUsageCounter`, operacionales. Aquí solo está el
    # límite, que es configuración y sí se sincroniza al edge.
    default_user_daily_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_user_monthly_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # De la organización entera, no de cada usuario: es el techo de gasto del contrato.
    monthly_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_chatbot_daily_token_quota: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
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
        # RAG.8. Admite NULL porque NULL significa «heredar», no «valor inválido»; son dos
        # estrategias estables con consumidor en el chunker, así que CHECK sí (mismo criterio
        # que `nivell_acces` en ING.0.2 y al contrario que el vocabulario de ámbitos).
        CheckConstraint(
            "chunking_strategy IS NULL OR chunking_strategy IN ('structural', 'parent_child')",
            name="ck_chatbot_chunking_strategy",
        ),
        # SEC.2.1. Tres modos, estables y con consumidor en `assert_chatbot_access`: esto
        # es estructura, no vocabulario. Añadir un cuarto exige escribir el código que lo
        # aplique, así que el CHECK no estorba a nadie (criterio de CLAUDE.md §5).
        CheckConstraint(
            "access_mode IN ('public_anon', 'authenticated', 'restricted')",
            name="ck_chatbot_access_mode",
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
    # --- Autorización por chatbot (SEC.2.1) ---
    #
    # `is_active` decía si un chatbot funciona; nada decía **para quién**. Dentro de una
    # organización todos quedaban igual de accesibles, así que un chatbot de gestión
    # interna era tan alcanzable como el público.
    #
    # El default es `authenticated` y no `public_anon` a propósito: un chatbot recién
    # creado no expone su corpus mientras nadie decida lo contrario.
    access_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="authenticated", server_default="authenticated"
    )
    # Dos ARRAY y **ninguna tabla de grants**: el atributo de grupo ya llega en el ACS SAML
    # y esto cubre el caso del piloto. Si algún día hace falta granularidad por persona, se
    # añade la tabla entonces; hoy sería infraestructura sin usuario.
    allowed_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    allowed_saml_groups: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    # --- Vigencia y presupuesto acumulado (SEC.4.1) ---
    #
    # Un chatbot de campaña —plazo de matrícula, convocatoria, alegaciones— tiene que poder
    # caducar solo. Hasta aquí la única palanca era que alguien se acordara de apagarlo.
    #
    # **No hay campo de estado.** Ni `closed_reason` ni voltear `is_active`: el estado se
    # calcula al preguntarlo. Un flag persistido se queda obsoleto y obliga a un job que lo
    # refresque, el consumo acumulado es dato operacional que no puede vivir en una tabla de
    # configuración, e `is_active` seguiría significando dos cosas a la vez —«el admin lo
    # apagó» y «se le pasó el plazo»— en un solo booleano.
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Lo que lee el ciudadano cuando el chatbot no está disponible. Vacío = mensaje genérico
    # del frontend: «el plazo de matrícula terminó el 30 de septiembre» lo escribe quien
    # gestiona el trámite, no un catálogo de errores.
    unavailable_message: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    # UX.4. Qué se contesta cuando NO hay fundamento suficiente, que es distinto de
    # `unavailable_message` —ese es cuando el chatbot está cerrado— y por eso es columna
    # propia y no un segundo significado de la misma. NULL = el texto genérico.
    #
    # Existe porque «no lo sé» a secas deja al ciudadano donde estaba, y a quién hay que
    # remitirlo depende del asistente: Infocampus atiende al público, no a gestión.
    no_answer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- Cuotas de consumo (SEC.4). NULL = heredar de la organización; 0 = sin límite ---
    user_daily_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chatbot_daily_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Para el widget anónimo (D.1), donde el sujeto no es una persona sino una IP. Sin
    # heredar de la organización: un chatbot público y uno interno no comparten criterio.
    anon_ip_daily_token_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- Campos del grafo público (9B.2) ---
    public_graph_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="PUBLIC_KB_RICH")
    language_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="prefer")
    quality_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    min_retrieval_results: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    min_retrieval_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reranker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answer_template: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    # Presupuesto de contexto en tokens para la inyección de documentos (VIS.2). NULL =
    # heredar de la organización y, en su defecto, del default de plataforma. Lo consume
    # LongContextRetrievalStrategy para RECORTAR, no para lanzar una excepción.
    context_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- Troceado (RAG.8). NULL = heredar; el CHECK admite NULL a propósito ---
    chunk_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_overlap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunking_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # RAG.10. NULL = heredar; un False no nulo haria que el chatbot pisara siempre a la
    # organizacion y encender la reescritura por organizacion no llegaria a ningun sitio.
    query_rewriting_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
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


class HubActivityPrompt(HubConfigBase):
    """Override del prompt y del nivel de una **actividad de plataforma** — PRO.2.1.

    `HubPromptTemplate` cuelga de un chatbot (`chatbot_id` NOT NULL), así que sirve a los
    prompts de un asistente y no a los de una actividad del módulo de Informes —escribir un
    script, auditarlo, transformar datos—, que no pertenecen a ningún chatbot.

    **No se resolvió haciendo `chatbot_id` nullable**: en Postgres una restricción unique con
    NULL no colisiona, así que `(chatbot_id, slug, language)` dejaría de ser única justo para
    las filas nuevas —dos overrides de la misma actividad conviviendo—, y la pantalla que
    filtra por chatbot perdería el sentido. Son dos claves distintas y dos audiencias
    distintas.

    Qué actividades existen, con qué nivel corren y qué se les dice lo dice el **código**
    (`modules/redaccion/services/actividades_llm.py`). Esta tabla guarda sólo la excepción:

    - `template_text` vacío o NULL = usa el texto del código. No se copia el texto por
      defecto al abrir la pantalla: copiarlo congelaría el prompt, y mejorarlo en el código
      no llegaría a quien ya lo abrió.
    - `override_tier` NULL = usa el nivel del código.
    """

    __tablename__ = "hub_activity_prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # La clave estable de la actividad (`ActividadLLM.value`). Única: una actividad, un override.
    activity: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    template_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


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
    # SEC.2.1. Sin esto, un usuario provisionado por SSO se quedaba con el claim de SEC.2
    # vacío y, por su propia regla, sin acceso a ningún recurso de organización.
    #
    # **Sale de la configuración del IdP (`SAML_ORGANIZACION_ID`), nunca de la aserción**:
    # si viniera de fuera, quien controla el IdP podría declarar a qué organización
    # pertenece cada persona que entra. Nullable porque un despliegue puede no haberla
    # configurado todavía, y ahí lo correcto es no dar acceso a nada.
    organizacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_organizaciones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


class HubTheme(HubConfigBase):
    """Tema de identidad visual (SEC.8.6).

    Vivían como ficheros `.json` bajo `data/themes`, ruta relativa al directorio de
    trabajo del proceso. En Cloud Run el contenedor es efímero y hay varias instancias:
    un tema creado en una desaparecía al reciclarse y no existía para las demás. El widget
    lo heredaba —resuelve el contenido desde el puntero `theme_config`— y volvía a quedarse
    sin tema en producción, con el puntero intacto.

    Es **configuración institucional**, no dato operacional del cliente: va en
    `HubConfigBase` y por tanto se sincroniza cloud→edge.

    `organizacion_id` nulo = tema **de plataforma**, que hereda la cascada entera; crearlo
    está reservado al superadministrador (SEC.2).
    """

    __tablename__ = "hub_themes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organizacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class HubWidgetKey(HubConfigBase):
    """Credencial de **sitio** para el widget público (SEC.8.5).

    El widget se incrustaba con `data-token`, y ese token era un JWT de sesión o un PAT
    completo: visible en el HTML de la página y con el rol y las organizaciones de su dueño
    detrás. SEC.2.1 ya había previsto la alternativa —`assert_chatbot_access` con
    `via='widget_api_key'` solo abre chatbots `public_anon`— pero no existía credencial que
    la usara.

    Tres propiedades, y las tres importan:

    - **Identifica un sitio, no a una persona.** No lleva rol ni organizaciones: lo único
      que autoriza es conversar con SU chatbot, y solo si es público.
    - **Vale para un chatbot.** `chatbot_id` no es un filtro que el endpoint aplique: es de
      dónde sale el chatbot, así que no hay forma de apuntarla a otro.
    - **Se guarda con hash**, como los PAT. El plano se enseña una vez al crearla.
    """

    __tablename__ = "hub_widget_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HubPlatformModule(HubConfigBase):
    """El catálogo de módulos de la plataforma, **como dato** (INF.7).

    Vive en tabla y no en un `Enum` de Python ni en un `CheckConstraint`, por la misma regla que
    el vocabulario del corpus: si los módulos fueran código, añadir uno exigiría una migración y
    un despliegue. `vigente` permite retirar uno sin borrar las concesiones que lo citan, que
    son el histórico de quién tuvo acceso a qué.

    En `HubConfigBase` porque es **configuración administrativa**: se decide en el cloud y el
    edge la necesita para saber si quien pide un informe puede pedirlo.
    """

    __tablename__ = "hub_platform_modules"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class HubModuleGrant(HubConfigBase):
    """Un módulo concedido a un usuario (INF.7).

    El sujeto es el id de usuario **normalizado a UUID** con `_actor.user_to_uuid`: no hay una
    tabla de usuarios única —hay `SuperAdminAccount` con `admin_id` entero y `AdminAccount` con
    `partner_id` de texto—, así que la clave estable es la que se deriva del claim del token.
    Ese normalizador existe precisamente por eso.
    """

    __tablename__ = "hub_module_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    #: Quién lo concedió. Un permiso sin autoría no se puede auditar.
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        UniqueConstraint("subject_id", "module_code", name="uq_grant_subject_module"),
    )
