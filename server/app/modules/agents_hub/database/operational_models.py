"""Modelos ORM operacionales para agents_hub."""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    # RAS.3 — la cola pendiente de una ejecución interrumpida, con lo ya visitado. Vivía sólo en
    # memoria: un corte en la página 8.000 obligaba a empezar de cero, y con la pausa de cortesía
    # eso son horas de peticiones repetidas contra el mismo servidor.
    crawl_frontier: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
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

    # RAS.2 — por qué esta página no se puede leer sin renderizar, si es el caso. La evidencia se
    # recoge al rastrear (es el único momento en que existe el HTML) y la lee el detector, que
    # corre después: con señales, la página se avisa como `needs_javascript` en vez de acusarla
    # de estar vacía. Lista vacía = se leyó bien.
    render_signals: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )

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

    # RAS.3 — de qué fallo se trata y cuántas veces se intentó. Un 404 es una respuesta («esto ya
    # no está») y un timeout es un fallo del que no se concluye nada sobre la página; sin
    # distinguirlos, los dos salían como hallazgo crítico y un rastreo con mala red se llenaba de
    # acusaciones falsas.
    error_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)


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
        # Indice de la rama lexica del hibrido (RAG.4).
        Index("ix_hub_document_chunks_tsv", "tsv", postgresql_using="gin"),
        # RAG.9: la guarda de espacio vectorial corre en CADA consulta de chat, y su pregunta
        # —"que pares (modelo, dimension) hay en este chatbot"— es un DISTINCT sobre todos los
        # chunks del chatbot. Con este indice es un recorrido solo-indice de entradas
        # estrechas; sin el, el caso bueno (no hay desajuste) obliga a leer el heap entero
        # por pregunta, que es la forma mas cara posible de responder "no pasa nada".
        # PIL.1 añade `embedding_task_type` a la tripleta que la guarda pregunta. Si se
        # quedara fuera del indice, el DISTINCT volveria al heap y la guarda dejaria de ser
        # barata justo despues de haberla hecho mas estricta.
        Index(
            "ix_hub_document_chunks_embedding_space",
            "chatbot_id",
            "embedding_model",
            "embedding_dim",
            "embedding_task_type",
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
    # --- Parent-child, small-to-big (RAG.8) ---
    # La seccion estructural completa a la que pertenece este fragmento. Se busca con el
    # hijo —vector mas especifico, se encuentra mejor— y se responde con el padre, que trae
    # el contexto que al hijo le falta. NULL con la estrategia 'structural'.
    # Columna directa y no JOIN: el padre ya existe como texto y duplicarlo cuesta menos que
    # una tabla de secciones que habria que mantener sincronizada con el troceado.
    parent_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- Procedencia del vector (MOD.1, obligatoria desde RAG.9) ---
    # Con que modelo y a que dimension se genero `embedding`. Misma dimension NO significa
    # mismo espacio vectorial: el coseno entre vectores de dos modelos distintos no da error,
    # da resultados malos. Sin esto, cambiar de modelo es una averia silenciosa.
    # NOT NULL tras el backfill de RAG.9: mientras existieron filas sin procedencia habia que
    # tratarlas como desconocidas, y "desconocido" es el hueco por el que se cuela justo la
    # averia que la columna vino a impedir. Rellenables => obligatorias.
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    # PIL.1. Nullable a propósito: el modelo local no distingue propósito y `None` es su
    # declaración honesta, no un dato que falte. Lo que NO puede pasar es que un corpus
    # embebido como consulta se sirva como documento sin que nadie lo note — de eso se
    # ocupa `assert_embedding_space_matches`, que compara la tripleta completa.
    embedding_task_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # El texto que SE EMBEBIO, que desde RAG.7 no es `content`: lleva delante titulo y
    # jerarquia. Se guarda para que re-embeber sea fiel — reconstruirlo desde `content`
    # produciria vectores que la ingesta nunca genero, y la incoherencia no daria error.
    # NULL en los chunks anteriores a RAG.9: no se puede reconstruir, asi que la CLI de
    # re-embedding los cuenta aparte y remite a `recalculate-corpus`, que si re-trocea.
    embedding_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- Rama lexica del hibrido (RAG.4) ---
    # Puente bilingue del dominio ('despesa/gasto'), copiado del documento en la ingesta.
    # Se DENORMALIZA aqui porque una columna generada solo puede referirse a su propia fila,
    # y los terminos viven en hub_documents.doc_metadata. Refrescarlos cuando cambien es un
    # UPDATE con JOIN, no un re-embedding: el invariante de CLAUDE.md §5 se conserva.
    # Aqui va SOLO el puente lexico; la taxonomia (ambit/submateries) no entra jamas.
    bilingual_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    # `simple` para todo lo que no sea castellano: PostgreSQL core no trae stemmer catalan,
    # asi que en catalan se busca por forma exacta. Un diccionario Snowball catalan seria
    # mejora de despliegue, no de codigo.
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector("
            "CASE WHEN language = 'es' THEN 'spanish'::regconfig "
            "ELSE 'simple'::regconfig END, "
            "coalesce(content, '') || ' ' || coalesce(bilingual_terms, ''))",
            persisted=True,
        ),
        nullable=True,
    )
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
    __table_args__ = (
        # REV.1: mismos tres valores que `ck_test_run_verdict`, a propósito. Dos vocabularios
        # distintos para la misma idea acaban divergiendo, y entonces un informe que cruce
        # escenarios de prueba con conversaciones reales deja de poder escribirse.
        # Admite NULL porque NULL es "sin revisar", no valor inválido.
        CheckConstraint(
            "review_verdict IS NULL OR review_verdict IN ('good', 'bad', 'mixed')",
            name="ck_interaction_review_verdict",
        ),
    )

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
    # SEC.4: consumo real de la interacción. **Nullable a propósito**: las interacciones
    # anteriores a este prompt no tienen el dato y no se inventa. Un cero significaría «no
    # gastó nada», que es una afirmación distinta de «no lo sabemos».
    #
    # De dónde salió el número se anota en `interaction_metadata.usage_source`
    # ('provider' | 'estimated'): una cuota apoyada en una estimación silenciosa es una
    # cuota que no se puede defender ante quien la sufre.
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # El chat no la rellena, y es deliberado: la tabla de precios (`ModelPricing`, que
    # alimenta OpenRouter) vive en la BD de plataforma, y el chat es **edge**. Convertir
    # tokens en euros es asunto de facturación —cloud—, que ya tiene `calculate_cost`. La
    # columna queda porque las cuotas se miden en tokens pero se justifican en dinero, y el
    # día que facturación lo calcule tiene dónde escribirlo sin migrar otra vez.
    cost_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)
    interaction_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # --- Veredicto de quien revisa (REV.1) ---
    # Distinto de `feedback_score`/`feedback_text`, que son la valoración del USUARIO FINAL.
    # Esto es lo que dice quien audita: si la respuesta era adecuada y, sobre todo, por qué
    # no lo era — que es lo único que permite reformular la FAQ que la produjo.
    #
    # NULL = sin revisar, y es el estado por defecto: es lo que alimenta la cola. Un texto
    # 'pending' sería un veredicto más, y habría que acordarse de excluirlo en cada consulta.
    review_verdict: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HubUsageCounter(HubOperationalBase):
    """Consumo acumulado por sujeto y ventana (SEC.4).

    **Vive en `HubOperationalBase` y no colgado del chatbot**, y no es un detalle: es dato de
    consumo del cliente final, no configuración, así que no se sincroniza al cloud. Un
    contador en `HubChatbot` rompería la frontera edge/cloud en cuanto la sync API empezara
    a copiar configuración.

    `window_key` es la ventana en texto —`'2026-08-02'` (día), `'2026-08'` (mes), `'total'`
    (acumulado, que reutiliza SEC.4.1)—. En texto y no como fecha porque las tres conviven
    en la misma columna y la clave única las distingue sin tabla aparte ni nulos.

    Se actualiza con un UPSERT atómico, nunca leyendo-modificando-escribiendo: el chat es
    concurrente y dos respuestas simultáneas del mismo usuario se pisarían los contadores,
    que es exactamente el hueco por el que se cuela quien quiera saltarse una cuota.
    """

    __tablename__ = "hub_usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_id", "window_key", name="uq_usage_counter_subject_window"
        ),
        CheckConstraint(
            "subject_type IN ('user', 'chatbot', 'organizacion', 'ip')",
            name="ck_usage_counter_subject_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    window_key: Mapped[str] = mapped_column(String(20), nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
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
    # --- Progreso y estadisticas por etapa (RAG.12) ---
    # `status` solo distingue pending/running/completed/failed, y una conversion de Docling
    # sobre un PDF largo tarda minutos: desde fuera, un job trabajando y un job colgado son
    # indistinguibles. Esto es estado CONSULTABLE, no mas log.
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # NULL mientras no se sabe: el total de fragmentos no existe hasta despues de trocear.
    progress_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_message: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # n_chunks, total_chars, n_batches, embedding_model, stage_ms{} y —si revento—
    # failed_stage. Se escribe TAMBIEN al fallar: es cuando mas falta hace saber por donde
    # iba, y lo acumulado vive en memoria, asi que sobrevive al rollback del manejador.
    processing_stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class HubContentFinding(HubOperationalBase):
    """Hallazgo de calidad: sobre una pagina/sitio (9Q) o sobre un chatbot (RAG.14)."""

    __tablename__ = "hub_content_findings"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "finding_type", "page_id", "related_page_id",
            name="uq_finding_dedup",
        ),
        # RAG.14: un hallazgo tiene UN sujeto, y ahora hay dos clases. Los de 9Q auditan
        # paginas y cuelgan de un sitio; los huecos de corpus nacen de conversaciones y
        # cuelgan de un chatbot — forzarles un sitio seria inventarle un sitio web a una
        # pregunta. Nullable NO significa opcional: sin sujeto, el hallazgo no se puede
        # revisar, y por eso el CHECK exige exactamente uno de los dos.
        CheckConstraint(
            "(site_id IS NULL) <> (chatbot_id IS NULL)",
            name="ck_finding_tiene_un_sujeto",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # RAG.14: sujeto alternativo al sitio, para los hallazgos que salen del uso y no de una
    # auditoria de paginas. Sin FK a hub_chatbots: es config (cloud) y esta tabla es
    # operacional (edge), y CLAUDE.md prohibe cruzar las dos bases.
    chatbot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
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


class HubTestScenario(HubOperationalBase):
    """Consulta guardada para probar un chatbot a mano, con lo que se espera de ella (RAG.13).

    Que exista esto y el dataset dorado de RAG.1 no es duplicidad: el dorado mide
    RECUPERACION con metricas automaticas y bloquea el build; esto mide la RESPUESTA con
    juicio humano, que es lo que ninguna metrica sustituye en un asistente normativo. Uno
    dice si el documento correcto sale entre los cinco primeros; el otro, si lo que se le
    contesta a una persona vale.

    Operacional y no de configuracion: son las pruebas del cliente sobre su propio corpus,
    asi que viven en el edge y no se sincronizan al cloud.
    """

    __tablename__ = "hub_test_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Turnos previos en el formato 'rol: texto' que consume el grafo (RAG.10). NULL = el
    # escenario es de un solo turno, que es el caso normal.
    history: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    # Que se espera de la respuesta, en prosa. NO se comprueba automaticamente a proposito:
    # convertirlo en una asercion exigiria un criterio de igualdad entre respuestas de un
    # LLM, y ese criterio es el problema, no la solucion. Es la nota que lee quien juzga.
    expectation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    runs: Mapped[list["HubTestRun"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )


class HubTestRun(HubOperationalBase):
    """Una ejecucion de un escenario y el veredicto humano que recibio (RAG.13)."""

    __tablename__ = "hub_test_runs"
    __table_args__ = (
        # Tres valores estables con consumidor en la UI: CHECK si, mismo criterio que
        # `purpose` en MOD.1 y al contrario que el vocabulario de ambitos (CLAUDE.md §5).
        # Admite NULL porque NULL es "sin juzgar todavia", no valor invalido.
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('good', 'bad', 'mixed')",
            name="ck_test_run_verdict",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_test_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Captura del bypass de RAG.11, solo si se pidio: el prompt final, el contexto empaquetado
    # y la configuracion resuelta EN EL MOMENTO de la ejecucion. Sin esto, un run de hace un
    # mes no se puede explicar, porque la configuracion ya no es la misma.
    bypass_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(10), nullable=True)
    verdict_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    scenario: Mapped["HubTestScenario"] = relationship(back_populates="runs")
