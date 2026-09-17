"""El diario de las pasadas de curación (DIN.6).

Deploy: edge — una pasada es trabajo sobre el portal de un cliente.

El `summary` del job se calculaba, se devolvía y **se perdía**. La confianza en una
automatización se construye pudiendo auditarla barata: si quien cura no ve lo que hizo, la
apagará al primer susto — y tendrá razón. Con DIN.4 y DIN.5 encima eso deja de ser una molestia y
pasa a ser el único sitio donde se puede ver que la salvaguarda paró una retirada o que la puerta
de calidad dejó fuera cinco páginas.

**Transacción propia**, como el repositorio de avisos de RAS.5: el diario es información sobre
algo que **ya pasó**, y perderla porque la transacción del job termine mal sería perder justo el
rastro del problema.

**Retención por ámbito y poda en la propia escritura.** La alternativa era un planificador nuevo
para limpiar una tabla que crece una fila por pasada: con cadencia de seis horas, una sección son
cuatro filas al día. Cincuenta pasadas son casi dos semanas de historia, que es el horizonte en
el que alguien pregunta «¿qué pasó aquí?»; y quien quiera más, sube el número.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from server.app.modules.agents_hub.database.operational_models import HubCrawlRun

logger = logging.getLogger(__name__)

#: Cuántas pasadas se conservan **por ámbito**. Por ámbito y no por sitio: si fuera por sitio,
#: la sección que se rastrea cada seis horas se llevaría todas las filas y borraría la historia
#: de la que se mira una vez a la semana.
PASADAS_CONSERVADAS = 50


class DiarioDePasadas:
    """Escribe y poda el diario. Una instancia por aplicación; una transacción por pasada."""

    def __init__(self, session_factory: Any, *, conservadas: int = PASADAS_CONSERVADAS) -> None:
        self._session_factory = session_factory
        self._conservadas = conservadas

    async def registrar(
        self,
        *,
        site_id: uuid.UUID,
        section_id: uuid.UUID | None,
        scope_label: str,
        started_at: datetime,
        finished_at: datetime,
        summary: Any,
    ) -> Any:
        """Deja constancia de una pasada y poda las viejas de su ámbito."""
        async with self._session_factory() as session:
            pasada = HubCrawlRun(
                site_id=site_id,
                section_id=section_id,
                scope_label=scope_label,
                started_at=started_at,
                finished_at=finished_at,
                pages_total=getattr(summary, "pages_total", 0),
                pages_new=getattr(summary, "pages_new", 0),
                pages_changed=getattr(summary, "pages_changed", 0),
                pages_gone=getattr(summary, "pages_gone", 0),
                pages_error=getattr(summary, "pages_error", 0),
                documents_auto_ingested=getattr(summary, "documents_auto_ingested", 0),
                documents_reingested=getattr(summary, "documents_reingested", 0),
                documents_auto_retired=getattr(summary, "documents_auto_retired", 0),
                pages_blocked_by_findings=getattr(summary, "pages_blocked_by_findings", 0),
                findings_retired=getattr(summary, "findings_retired", 0),
                truncated=bool(getattr(summary, "truncated", False)),
                stop_reason=getattr(summary, "stop_reason", None),
                # Acotado: una pasada contra un portal roto puede traer cientos de errores, y la
                # fila del diario no es el sitio donde guardar un log entero.
                errors=[str(e)[:500] for e in (getattr(summary, "errors", None) or [])][:50],
            )
            session.add(pasada)
            await session.flush()
            await self._podar(session, site_id, section_id)
            await session.commit()
            return pasada

    async def _podar(
        self, session: Any, site_id: uuid.UUID, section_id: uuid.UUID | None
    ) -> int:
        """Deja las últimas N pasadas de **este** ámbito. No toca las de otro ni las de otro sitio.

        El desempate por `id` no es decoración: dos pasadas del mismo ámbito pueden compartir
        `started_at` al microsegundo, y sin él la poda dejaría en manos del planificador cuál se
        borra — o borraría la misma dos veces y ninguna otra.
        """
        consulta = select(HubCrawlRun).where(HubCrawlRun.site_id == site_id)
        consulta = (
            consulta.where(HubCrawlRun.section_id.is_(None))
            if section_id is None
            else consulta.where(HubCrawlRun.section_id == section_id)
        )
        filas = (
            await session.execute(
                consulta.order_by(HubCrawlRun.started_at.desc(), HubCrawlRun.id.desc())
            )
        ).scalars().all()

        sobrantes = list(filas)[self._conservadas :]
        for fila in sobrantes:
            await session.delete(fila)
        if sobrantes:
            await session.flush()
        return len(sobrantes)
