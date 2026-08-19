"""Contratos Pydantic para la gestión de sitios y selecciones (9Q.7).

Deploy: edge.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CrawlConfig(BaseModel):
    """Cómo se rastrea un apartado (RAS.5).

    El spider ya leía todo esto de `config_json`, pero **no había forma de fijarlo**: ni al crear
    ni al modificar un sitio. Sin `url_regex_filter` la decisión operativa del bloque —un sitio por
    apartado, porque cada apartado tiene un responsable distinto— era inalcanzable desde la
    interfaz, y el rastreo salía con los valores por defecto contra todo el dominio.

    Los defectos son los conservadores de RAS.1: la cortesía no se pide, se hereda.
    """

    crawl_depth: int = Field(default=1, ge=0, le=10)
    #: Expresión regular que acota el apartado. Se valida al guardar: una que no compila rompería
    #: todos los rastreos del sitio, y el fallo saldría lejos del formulario donde se escribió.
    url_regex_filter: str | None = None
    max_pages: int = Field(default=50, ge=1, le=100_000)
    #: Presupuesto de tiempo por ejecución, en segundos. Con pausa de cortesía, el coste real de un
    #: rastreo es el tiempo: mil páginas a un segundo son veinte minutos.
    max_seconds: int = Field(default=1800, ge=10, le=86_400)
    delay_seconds: float = Field(default=1.0, ge=0.0, le=60.0)
    respect_robots: bool = True
    max_concurrency: int = Field(default=1, ge=1, le=8)
    max_retries: int = Field(default=3, ge=1, le=10)

    # CUR.1 — de dónde sacar la fecha que **publica** la página y la unidad que la mantiene. El
    # marcado es de cada portal (`www.uji.es` las sirve juntas en `.clockBarDate`), así que va en la
    # configuración del sitio: hardcodearlo acoplaría el módulo a un cliente. Vacío = como antes.
    content_date_selector: str | None = None
    content_date_format: str = "%d/%m/%Y"

    # CUR.2.1 — los **criterios de juicio**, por sitio y por tanto por organización. Estaban en el
    # código: `stale_days` y el umbral de contenido pobre los ponía el constructor del detector y
    # nadie los pasaba, y la semántica de una serie por años se fijó global a partir de cómo publica
    # un portal concreto. Un portal de normativa y uno de noticias no envejecen igual, y donde la
    # UJI publica series vigentes otro versiona convocatorias. Es la misma regla que el proyecto ya
    # aplica al vocabulario del corpus: **el criterio es dato, no código**.
    #
    # Los defectos son los de hoy, para no cambiarle el criterio a nadie al desplegar esto.
    # CUR.3 — qué parte de la página es contenido y qué es plantilla. Al corpus tiene que ir sólo
    # lo primero: medido en el portal, cada página lleva el menú completo, y el asistente lo cita.
    # `content_selector` es la señal más fuerte cuando el portal la ofrece (`main` aquí);
    # `boilerplate_selectors` quita lo que está dentro del contenido y sigue siendo plantilla
    # —miga de pan, barra de fecha, iconos de compartir—.
    content_selector: str | None = None
    boilerplate_selectors: list[str] = Field(default_factory=list)
    #: Proporción de páginas en las que una línea tiene que aparecer para tenerse por plantilla.
    boilerplate_repeat_threshold: float = Field(default=0.6, gt=0.0, le=1.0)

    stale_days: int = Field(default=365, ge=1, le=36_500)
    thin_min_tokens: int = Field(default=120, ge=0, le=100_000)
    #: `series` — varias versiones por año y **todas vigentes** (la UJI: acuerdos y actas).
    #: `superseded` — la nueva deroga a la vieja (un portal que versiona convocatorias).
    #: `off` — el año de la URL no significa nada aquí; agrupar sólo daría ruido.
    version_series_policy: Literal["series", "superseded", "off"] = "series"

    @field_validator("content_date_format")
    @classmethod
    def _debe_ser_un_formato_de_fecha(cls, valor: str) -> str:
        """Un formato inválido fallaría en **cada página** del rastreo, lejos del formulario."""
        from datetime import datetime

        try:
            datetime.strptime(datetime(2026, 1, 2).strftime(valor), valor)
        except (ValueError, TypeError) as fallo:
            raise ValueError(
                f"«{valor}» no es un formato de fecha de `strftime` válido: {fallo}"
            ) from fallo
        if valor.strip() == datetime(2026, 1, 2).strftime(valor).strip():
            # Una cadena sin directivas (`no es un formato`) «formatea» a sí misma: no es un
            # formato, es texto.
            raise ValueError(f"«{valor}» no lleva ninguna directiva de fecha (%d, %m, %Y…)")
        return valor

    @field_validator("url_regex_filter")
    @classmethod
    def _debe_compilar(cls, valor: str | None) -> str | None:
        if valor is None or not valor.strip():
            return None
        try:
            re.compile(valor)
        except re.error as fallo:
            raise ValueError(
                f"«{valor}» no es una expresión regular válida: {fallo}"
            ) from fallo
        return valor


class SiteView(BaseModel):
    id: uuid.UUID
    organizacion_id: uuid.UUID | None
    name: str
    root_url: str
    sitemap_url: str | None
    spider_type: str
    crawl_interval_hours: int
    audit_semantic_scope: str
    last_crawled_at: datetime | None
    status: str
    created_at: datetime
    #: RAS.5 — quien mira la lista tiene que poder ver con qué cortesía y con qué filtro se está
    #: rastreando cada apartado. Antes no salía, así que no había forma de revisarlo.
    crawl_config: CrawlConfig | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _desde_config_json(cls, datos: Any) -> Any:
        """La configuración vive en `config_json` en la base; aquí se sirve tipada."""
        if isinstance(datos, dict) or not hasattr(datos, "config_json"):
            return datos
        crudo = getattr(datos, "config_json", None) or {}
        campos = {k: v for k, v in crudo.items() if k in CrawlConfig.model_fields}
        return {
            **{
                nombre: getattr(datos, nombre, None)
                for nombre in cls.model_fields
                if nombre != "crawl_config"
            },
            "crawl_config": CrawlConfig(**campos) if campos else None,
        }


class SiteCreate(BaseModel):
    name: str
    root_url: str
    sitemap_url: str | None = None
    audit_semantic_scope: str = "ingested"
    crawl_interval_hours: int = 24
    crawl_config: CrawlConfig | None = None


class SitePatch(BaseModel):
    name: str | None = None
    root_url: str | None = None
    sitemap_url: str | None = None
    audit_semantic_scope: str | None = None
    crawl_interval_hours: int | None = None
    crawl_config: CrawlConfig | None = None


class PageView(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    url: str
    title: str | None
    status: str
    token_count: int | None
    superseded: bool
    quality_score: float | None
    last_crawled_at: datetime | None

    model_config = {"from_attributes": True}


class SelectionView(BaseModel):
    id: uuid.UUID
    chatbot_id: uuid.UUID
    site_id: uuid.UUID
    rule_type: str
    rule_value: str | None
    auto_ingest_new: bool
    created_at: datetime

    model_config = {"from_attributes": True}


#: Los tipos de regla que `SelectionRepo.matches` sabe evaluar. Cualquier otro se guardaba
#: con un 201 y no casaba nunca: en la pantalla, una selección activa y ninguna página
#: seleccionada, sin nada que explicara por qué (VER.8). Mismo criterio que el spider
#: desconocido del dispatcher: fallar donde se ve, no caer a algo que parece funcionar.
TiposDeRegla = Literal["path_prefix", "sitemap_section", "manual"]


class SelectionCreate(BaseModel):
    site_id: uuid.UUID
    rule_type: TiposDeRegla
    rule_value: str | None = None
    auto_ingest_new: bool = True


class CandidatePageView(BaseModel):
    page_id: uuid.UUID
    url: str
    title: str | None
    matched_rule: str | None
    is_new: bool
