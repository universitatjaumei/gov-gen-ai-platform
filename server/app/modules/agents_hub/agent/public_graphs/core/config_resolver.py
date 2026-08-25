"""ConfigResolver: resuelve la configuración efectiva del grafo público.

Cascada: PlatformDefaults → OrgDefaults (HubOrganizacion) → ChatbotOverrides (HubChatbot).
Un campo None en el chatbot o el org indica "heredar del nivel superior".

Deploy: edge
"""
import uuid
from dataclasses import dataclass, replace
from typing import Any


@dataclass
class PublicGraphConfig:
    profile: str
    retrieval_mode: str
    language_mode: str
    quality_threshold: float
    # Cuántos resultados hacen falta para **no penalizar** la respuesta en el gate de calidad. Es
    # un suelo, no una anchura — ver `retrieval_top_k` más abajo, que es su pareja y con la que se
    # confundía: mezclarlos hacía que subir el mínimo ampliara la recuperación **y** a la vez
    # hiciera más probable el castigo, porque `len(items) >= min` sólo se cumplía recuperando
    # exactamente todos los que cabían.
    min_retrieval_results: int
    min_retrieval_score: float
    reranker_enabled: bool
    answer_template: str
    chatbot_id: uuid.UUID | None = None
    # RAG.2: el system_prompt del chatbot entra por la cascada porque *es* configuración
    # efectiva del chatbot. Así la TemplateStrategy —única fuente del system prompt— lo
    # recibe por el mismo camino que el resto de la config, sin parámetros paralelos.
    system_prompt: str | None = None
    # UX.4: qué se contesta cuando no hay fundamento suficiente. `None` = el texto genérico
    # de `citation_validator`. Se configura por chatbot porque el destino al que se remite
    # depende de a quién sirve: Infocampus atiende al público, no al personal de gestión.
    no_answer_message: str | None = None
    # VIS.2: presupuesto de contexto para la inyección de documentos. Mismo argumento que
    # el system_prompt para entrar por aquí.
    #
    # El default de plataforma son 128.000 tokens porque el Nivel 2 inyecta documentos
    # ENTEROS (1-3 normas, ~25k).
    #
    # **Decidido por el usuario el 2026-07-31: 128.000 con carácter general.** El prompt de
    # RAG.5 pide un default de plataforma de 4.000 para su empaquetador de chunks; queda
    # anulado. Un mismo valor no puede significar dos cosas según quién lo lea, y bajarlo
    # aquí recortaría MD_LONG_CONTEXT a 4k, o sea lo dejaría inservible. RAG.5 consume este
    # presupuesto tal cual; si su packer necesita cortar antes, es una decisión del packer
    # con su propia constante, no un cambio de este default.
    context_token_budget: int = 128_000
    # VIS.2 (Nivel 0): índice de submaterias del vocabulario de la organización. Se resuelve
    # solo en MD_AGENT_SELECTOR —en RAG serían ~2.300 tokens de prompt que nadie usa— y
    # entra por la cascada porque depende de la organización del chatbot, igual que el resto.
    router_index: str | None = None
    # RAG.8: parámetros de troceado. Viven en la misma cascada que el resto porque son
    # configuración del chatbot, y el watcher los lee en vez de hardcodear los defaults.
    chunk_size: int = 1000
    chunk_overlap: int = 100
    chunking_strategy: str = "structural"
    # RAG.10: reescritura de la consulta con el historial antes de recuperar. **False de
    # plataforma**, por el mismo motivo que `reranker_enabled` y `min_retrieval_score`:
    # cuesta una llamada al LLM por turno de seguimiento y su ganancia no se ha medido
    # todavía contra el corpus real. Se enciende por chatbot cuando el gate lo respalde.
    query_rewriting_enabled: bool = False
    # LLM de reescritura, configurable en la organización porque es otro modelo —pequeño y
    # rápido— y no tiene sentido repetirlo en cada chatbot. None = usar el del chatbot con
    # el tope de salida bajado.
    rewrite_llm_config_id: uuid.UUID | None = None
    # RAG.15 — **cuántos fragmentos se recuperan**. No estaba en esta configuración: vivía en
    # `hub_chatbots.retrieval_top_k`, se podía editar desde el panel y **no llegaba hasta aquí**,
    # así que ningún pipeline podía leerlo y los dos que construían la recuperación usaban
    # `min_retrieval_results` en su lugar.
    #
    # Va en el bloque con valor por omisión y no junto a su pareja de arriba por una razón
    # prosaica: un campo obligatorio aquí rompe a todo el que construya la configuración a mano,
    # y hay unos cuantos dobles de test que sólo declaran lo que les interesa. El 8 es el mismo
    # que ya declaraba el modelo, así que nada cambia de valor — sólo empieza a leerse.
    retrieval_top_k: int = 8


_PLATFORM_DEFAULTS = PublicGraphConfig(
    profile="PUBLIC_KB_RICH",
    retrieval_mode="RAG",
    language_mode="prefer",
    quality_threshold=0.6,
    # RAG.15 — el mismo 8 que ya declaraba `hub_chatbots.retrieval_top_k` desde que se escribió.
    # Se conserva el valor **y se deja dicho que no está medido**: nadie lo leía, así que nunca
    # se comprobó contra el dorado. Elegirlo con datos es el trabajo que el prompt deja abierto,
    # y hacerlo exige el corpus real cargado.
    retrieval_top_k=8,
    min_retrieval_results=2,
    # RAG.5: el umbral está implementado y probado, pero **desactivado por defecto**, y el
    # 0.0 es una decisión con medición detrás. Con el default anterior (0,25) el dataset
    # dorado caía de recall@5 0,960 a 0,720 y MRR 0,861 a 0,693.
    #
    # Ese 0,72 NO prueba que 0,25 sea mal umbral en producción: el corpus de fixture usa un
    # embedding determinista (bolsa de palabras por hash) cuyas similitudes coseno son
    # estructuralmente bajas —una consulta de 6 palabras contra un fragmento de 100 rara vez
    # pasa de 0,25 aunque sea el acierto correcto—, y BGE-M3 tiene otra distribución. Un
    # umbral ABSOLUTO es justo lo que ese corpus no puede calibrar.
    #
    # Así que ni se calibra contra la distribución equivocada ni se deja activo un filtro
    # que recorta un 24 % de recall en lo único medible: se deja el mecanismo listo y la
    # activación pendiente de medir con el corpus real cargado. Decidido con el usuario el
    # 2026-08-01. Lo vigila `test_should_not_lose_golden_hits_with_the_default_threshold`.
    min_retrieval_score=0.0,
    # RAG.6 / decisión del usuario (2026-08-01): **el mecanismo se construye, el interruptor
    # no se enciende**. Con el default en True, en cuanto exista la implementación el
    # reranker se activaría de golpe para todos los chatbots, y eso (a) acopla la
    # disponibilidad del chat a un segundo servicio —el prompt exige error explícito, no
    # fallback—, (b) añade latencia y coste por consulta y (c) no se ha medido que mejore.
    # Es exactamente lo que pasó con min_retrieval_score, activo por defecto y recortando 24
    # puntos de recall sin que nadie lo hubiera comprobado. Se activa por chatbot cuando el
    # gate de RAG.1 lo respalde.
    reranker_enabled=False,
    answer_template="generic",
    context_token_budget=128_000,
)


def _apply_layer(config: PublicGraphConfig, values: dict[str, Any]) -> PublicGraphConfig:
    """Devuelve un nuevo PublicGraphConfig con los campos no-None de values aplicados."""
    overrides = {k: v for k, v in values.items() if v is not None}
    return replace(config, **overrides) if overrides else config


async def get_effective_public_graph_config(
    chatbot_id: uuid.UUID,
    session: Any,
) -> PublicGraphConfig:
    """Resuelve la configuración efectiva del grafo público para un chatbot.

    Aplica cascada: plataforma → organización → chatbot.
    """
    from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion

    config = replace(_PLATFORM_DEFAULTS, chatbot_id=chatbot_id)

    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        return config

    organizacion = await session.get(HubOrganizacion, chatbot.organizacion_id)
    if organizacion is not None:
        config = _apply_layer(config, {
            "profile":               organizacion.default_public_graph_profile,
            "retrieval_mode":        organizacion.default_retrieval_mode,
            "language_mode":         organizacion.default_language_mode,
            "quality_threshold":     organizacion.default_quality_threshold,
            "min_retrieval_results": organizacion.default_min_retrieval_results,
            "min_retrieval_score":   organizacion.default_min_retrieval_score,
            "reranker_enabled":      organizacion.default_reranker_enabled,
            "answer_template":       organizacion.default_answer_template,
            "context_token_budget":  organizacion.default_context_token_budget,
            "chunk_size":            organizacion.default_chunk_size,
            "chunk_overlap":         organizacion.default_chunk_overlap,
            "chunking_strategy":     organizacion.default_chunking_strategy,
            "query_rewriting_enabled": organizacion.default_query_rewriting_enabled,
            "rewrite_llm_config_id": organizacion.rewrite_llm_config_id,
        })

    config = _apply_layer(config, {
        "profile":               chatbot.public_graph_profile,
        "retrieval_mode":        chatbot.retrieval_mode,
        "system_prompt":         chatbot.system_prompt,
        "no_answer_message":     chatbot.no_answer_message,
        "language_mode":         chatbot.language_mode,
        "quality_threshold":     chatbot.quality_threshold,
        # RAG.15 — la anchura del chatbot entra por fin en la configuración efectiva. No hay
        # capa de organización para ella porque `hub_organizaciones` no declara
        # `default_retrieval_top_k`: añadirla es una columna nueva y una decisión de producto que
        # este prompt no necesita, así que la cadena es chatbot → plataforma.
        "retrieval_top_k":       chatbot.retrieval_top_k,
        "min_retrieval_results": chatbot.min_retrieval_results,
        "min_retrieval_score":   chatbot.min_retrieval_score,
        "reranker_enabled":      chatbot.reranker_enabled,
        "answer_template":       chatbot.answer_template,
        "context_token_budget":  chatbot.context_token_budget,
        "chunk_size":            chatbot.chunk_size,
        "chunk_overlap":         chatbot.chunk_overlap,
        "chunking_strategy":     chatbot.chunking_strategy,
        "query_rewriting_enabled": chatbot.query_rewriting_enabled,
    })

    if config.retrieval_mode == "MD_AGENT_SELECTOR":
        config = replace(
            config,
            router_index=await _build_router_index(chatbot.organizacion_id, session),
        )

    return config


async def _build_router_index(organizacion_id: uuid.UUID, session: Any) -> str | None:
    """Índice de submaterias del Nivel 0, vía ConfigProvider (nunca el ORM del vocabulario).

    Devuelve None si la organización no tiene vocabulario cargado: el system prompt se
    compone igual y el modo selector degrada al catálogo de documentos, que es el
    comportamiento previo a VIS.2. Un vocabulario vacío no es un error de configuración.
    """
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.vocabulary_service import VocabularyService

    servicio = VocabularyService(LocalConfigProvider(session), organizacion_id)
    index = await servicio.build_router_index()
    return index or None
