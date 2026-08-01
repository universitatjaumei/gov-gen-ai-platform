"""Modelos ORM operacionales para agents_hub."""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from server.app.modules.agents_hub.database.base import HubOperationalBase


class HubWebSite(HubOperationalBase):
    """Sitio web rastreado. Unidad de crawl + auditoría; propiedad de la organización, no del chatbot."""

    __tablename__ = "hub_web_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organizacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sitemap_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    spider_type: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    crawl_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    audit_semantic_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ingested"
    )
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubCrawledPage(HubOperationalBase):
    """Página rastreada de un sitio. Acumula señales de frescura y flags de higiene."""

    __tablename__ = "hub_crawled_pages"
    __table_args__ = (
        UniqueConstraint("site_id", "url", name="uq_page_site_url"),
        # HNSW sobre el embedding de pagina (RAG.3): lo consulta por coseno el detector
        # semantico de 9Q. Declarado tambien en la migracion; ambos sitios, o la BD de los
        # tests (create_all) no lo tendria.
        Index(
            "ix_hub_crawled_pages_embedding_hnsw",
            "page_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"page_embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # embedding de página para auditoría semántica en modo "full" (9Q.4).
    # Misma dimensión que HubDocumentChunk.embedding (BGE-M3 = 1024) para que cruce coseno.
    # None = sin embedding (no auditada en modo full todavía).
    page_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)

    # señales de actualidad (las pobla 9Q.2)
    http_last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    http_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sitemap_lastmod: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    declared_canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # flags de higiene (los consolida 9Q.5)
    superseded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    superseded_by_page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class HubCorpusSelection(HubOperationalBase):
    """Selección N:M chatbot→sitio. La regla decide qué páginas alimentan el corpus."""

    __tablename__ = "hub_corpus_selections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_value: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    auto_ingest_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubDocument(HubOperationalBase):
    """Documento citable. Unidad atomica del corpus de un chatbot.

    Metadatos del corpus normativo (ING.0.2). **Regla que decide el esquema**: una
    columna de primer nivel SOLO si algo la filtra, la ordena o la usa como puerta;
    todo lo demas va a `doc_metadata` JSONB. Sin esa disciplina los 56 campos del
    esquema de metadatos (`vocabulari/esquema_metadades.yaml`) acabarian aqui.

    Los codigos de vocabulario (`ambit_principal`, `submateries`) **no llevan
    CheckConstraint**: son dato revisable y se validan en la capa de contrato
    (ING.0.3) contra `HubVocabularyTerm`. Ver CLAUDE.md §5. `nivell_acces`,
    `us_assistents` y `content_class` si lo llevan: son enumeraciones estables con
    consumidor (filtrado fail-closed de VIS.1).

    `source_kind` expresa el origen y sus valores documentados son
    'crawler' | 'upload' | 'publicacio' | 'boe'. No hay columna `origen` aparte:
    duplicar el eje seria deuda.
    """

    __tablename__ = "hub_documents"
    __table_args__ = (
        UniqueConstraint("chatbot_id", "content_hash", name="uq_document_chatbot_hash"),
        CheckConstraint(
            "nivell_acces IN ('public', 'intern', 'restringit')",
            name="ck_document_nivell_acces",
        ),
        CheckConstraint(
            "us_assistents IN ('si', 'restringit', 'no')",
            name="ck_document_us_assistents",
        ),
        CheckConstraint(
            "content_class IN ('regulation', 'faq', 'generic')",
            name="ck_document_content_class",
        ),
        Index("ix_hub_documents_chatbot_ambit", "chatbot_id", "ambit_principal"),
        Index("ix_hub_documents_chatbot_nivell", "chatbot_id", "nivell_acces"),
        Index(
            "ix_hub_documents_submateries",
            "submateries",
            postgresql_using="gin",
        ),
        Index(
            "ix_hub_documents_submateries_internes",
            "submateries_internes",
            postgresql_using="gin",
        ),
        Index(
            "ix_hub_documents_doc_metadata",
            "doc_metadata",
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crawled_page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_crawled_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # --- Clasificacion (ING.0.2). Vocabulario validado en ING.0.3, no con CHECK ---
    content_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generic"
    )
    ambit_principal: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # ARRAY del dialecto PostgreSQL y no el genérico: VIS.1 filtra con el operador de
    # solapamiento `&&` (`.overlap()`), que solo expone el tipo del dialecto.
    ambits_secundaris: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String), nullable=False, default=list
    )
    submateries: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String), nullable=False, default=list
    )
    submateries_internes: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String), nullable=False, default=list
    )
    # --- Acceso y uso. nivell_acces se impone en la capa de recuperacion (VIS.1) ---
    nivell_acces: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public"
    )
    us_assistents: Mapped[str] = mapped_column(
        String(20), nullable=False, default="si"
    )
    # --- Version idiomatica: solo la canonica se indexa (VIS.3) ---
    canonica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    versio_idiomatica_de: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    # --- Vigencia. vigencia_validada_el NULL => el asistente ADVIERTE (VIS.3) ---
    estat_vigencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vigencia_validada_el: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revisat_per: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revisat_el: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_revisio_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    # --- Sincronizacion con el registro de publicacion (SYNC.1) ---
    id_publicacio: Mapped[str | None] = mapped_column(
        String(80), nullable=True, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # --- El resto del esquema de 56 campos ---
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubDocumentChunk(HubOperationalBase):
    """Fragmento de documento con embedding vectorial."""

    __tablename__ = "hub_document_chunks"
    __table_args__ = (
        # Indice ANN de la busqueda vectorial (RAG.3). Sin el, cada consulta calcula la
        # distancia coseno contra todos los chunks del chatbot: un escaneo secuencial por
        # pregunta. `vector_cosine_ops` porque `retriever.py` ordena por `cosine_distance`;
        # un opclass distinto dejaria el indice inservible para esa consulta.
        Index(
            "ix_hub_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # FK añadida en ING.0.2: VIS.1 filtra los chunks por los metadatos de su documento
    # mediante JOIN. Nullable porque los chunks temporales de subida de usuario no
    # tienen documento (los acota owner_id).
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    is_temporary: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubInteraction(HubOperationalBase):
    """Conversación usuario–asistente."""

    __tablename__ = "hub_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_message: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    feedback_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'quality_gate' | 'citation' | NULL. NULL = la respuesta salió del camino normal.
    # RAG.14 lo consume para detectar huecos de corpus. Sin CheckConstraint: los motivos
    # son un vocabulario que crecerá (reranker, presupuesto de tokens...) y una restricción
    # en la BD obligaría a una migración por cada motivo nuevo.
    fallback_reason: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    interaction_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubIngestionJob(HubOperationalBase):
    """Job de ingestión de documentos."""

    __tablename__ = "hub_ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    chunks_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubContentFinding(HubOperationalBase):
    """Hallazgo de calidad sobre una página o sitio web. Keyed a sitio/página, no a chatbot."""

    __tablename__ = "hub_content_findings"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "finding_type", "page_id", "related_page_id",
            name="uq_finding_dedup",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_crawled_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    signal_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("status", "new")
        super().__init__(**kwargs)
