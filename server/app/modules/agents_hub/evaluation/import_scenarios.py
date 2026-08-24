"""Importación de un lote de escenarios de prueba desde un fichero JSON. Deploy: edge.

Los escenarios de RAG.13 se crean de uno en uno por la API, que es lo correcto cuando alguien
piensa una prueba mientras usa el asistente. Un lote no: una batería de consultas reales con el
veredicto que un informador le puso a cada una no se teclea una a una sin perder por el camino
justo el matiz que la hace valiosa.

    uv run python -m server.app.modules.agents_hub.evaluation.import_scenarios \\
        --dataset <ruta.json> --chatbot-id <uuid> [--created-by alguien@uji.es]

**El fichero del lote no vive en el repositorio.** Es material de evaluación de un cliente
concreto y el repositorio es público: se versiona el mecanismo, no los datos.

**Idempotente por (chatbot, nombre)**: reimportar actualiza, no duplica. Un lote se corrige
—se afina una nota, se añade una fuente esperada— y hay que poder volver a cargarlo sin dejar
dos copias que quien juzga no sabe distinguir. Y la clave lleva el chatbot dentro porque
importar el mismo lote en dos chatbots es exactamente cómo se comparan dos configuraciones.

El bloque `meta` de cada escenario —informador, veredicto que le puso, modos de fallo— **no
entra en la base de datos**. Es procedencia del fichero, no estado del sistema, y añadir una
columna JSONB para guardarlo dejaría el dato donde nadie lo lee: lo que hace falta al juzgar
una respuesta ya está redactado dentro de `expectation_note`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import select

from server.app.modules.agents_hub.database.operational_models import HubTestScenario


class EscenarioDelLote(BaseModel):
    """Un escenario tal y como viaja en el fichero.

    `extra="allow"` a propósito: `meta` viaja con cada escenario y se descarta al persistir,
    pero prohibirlo obligaría a quien enriquece el lote a tocar este modelo, y el fichero es
    dato revisable a mano.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    prompt: str
    history: list[str] | None = None
    expectation_note: str | None = None

    @field_validator("name", "prompt")
    @classmethod
    def _no_vacio(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("un escenario sin nombre o sin consulta no prueba nada")
        return valor


class LoteDeEscenarios(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    scenarios: tuple[EscenarioDelLote, ...] = ()

    @model_validator(mode="after")
    def _sin_nombres_repetidos(self) -> "LoteDeEscenarios":
        vistos = [e.name.strip() for e in self.scenarios]
        repetidos = {n for n in vistos if vistos.count(n) > 1}
        if repetidos:
            raise ValueError(
                f"nombres repetidos en el lote: {sorted(repetidos)}; el segundo pisaría al "
                "primero al importar y el lote parecería completo con uno menos"
            )
        return self


@dataclass(frozen=True)
class ResumenImportacion:
    creados: int
    actualizados: int


def cargar_lote(path: Path | str) -> LoteDeEscenarios:
    datos = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return LoteDeEscenarios(**datos)


async def importar_escenarios(
    session,
    chatbot_id: uuid.UUID,
    lote: LoteDeEscenarios,
    created_by: str | None = None,
) -> ResumenImportacion:
    """Crea o actualiza los escenarios del lote en un chatbot. Devuelve cuántos de cada."""
    existentes = {
        fila.name: fila
        for fila in (
            (
                await session.execute(
                    select(HubTestScenario).where(
                        HubTestScenario.chatbot_id == chatbot_id
                    )
                )
            )
            .scalars()
            .all()
        )
    }

    creados = actualizados = 0
    for escenario in lote.scenarios:
        fila = existentes.get(escenario.name)
        if fila is None:
            session.add(
                HubTestScenario(
                    chatbot_id=chatbot_id,
                    name=escenario.name,
                    prompt=escenario.prompt,
                    history=escenario.history,
                    expectation_note=escenario.expectation_note,
                    created_by=created_by,
                )
            )
            creados += 1
            continue
        fila.prompt = escenario.prompt
        fila.history = escenario.history
        fila.expectation_note = escenario.expectation_note
        fila.updated_at = datetime.now(timezone.utc)
        actualizados += 1

    await session.commit()
    return ResumenImportacion(creados=creados, actualizados=actualizados)


async def _run(args: argparse.Namespace) -> int:
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )

    lote = cargar_lote(args.dataset)
    engine = create_async_engine()
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            resumen = await importar_escenarios(
                session, args.chatbot_id, lote, created_by=args.created_by
            )
    finally:
        await engine.dispose()

    print(
        f"Lote '{lote.name}': {resumen.creados} creados, "
        f"{resumen.actualizados} actualizados en el chatbot {args.chatbot_id}."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--chatbot-id", required=True, type=uuid.UUID)
    parser.add_argument("--created-by", default=None)
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
