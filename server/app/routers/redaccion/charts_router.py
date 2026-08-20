"""Charts router — preview de gráficos sin persistencia (9R.5.7).

Deploy: edge
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from server.app.core.sandbox_client import SandboxClient, get_sandbox_client
from server.app.modules.redaccion.services.charts.chart_configuration import ChartConfiguration
from server.app.modules.redaccion.services.charts.deterministic_chart_service import DeterministicChartService
from server.app.modules.redaccion.services.charts.chart_renderer import render_chart_from_script, ChartRenderError
from server.app.api.deps import require_module

router = APIRouter(prefix="/redaccion/charts", tags=["redaccion-charts"],
    # INF.7 — el modulo se exige a nivel de router: asi no se puede olvidar en un
    # endpoint nuevo del mismo fichero, que es como se abrieron los agujeros que SEC.8.1
    # tuvo que cerrar uno a uno.
    dependencies=[Depends(require_module("informes"))],
)


class DeterministicPreviewRequest(BaseModel):
    config: ChartConfiguration
    rows: list[dict[str, Any]]


class AIPreviewRequest(BaseModel):
    nl_prompt: str
    rows: list[dict[str, Any]]
    output_format: Literal["png", "svg"] = "png"


@router.post(
    "/preview/deterministic",
    summary="Preview determinista de gráfico",
    response_class=Response,
)
async def preview_deterministic(body: DeterministicPreviewRequest) -> Response:
    """Renderiza un gráfico determinista a partir de config + datos en línea.

    No persiste nada. Devuelve bytes PNG o SVG.
    """
    if not body.rows:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="rows cannot be empty")

    df = pd.DataFrame(body.rows)
    svc = DeterministicChartService()
    try:
        image_bytes = svc.render(df, body.config)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    media_type = "image/svg+xml" if body.config.output_format == "svg" else "image/png"
    return Response(content=image_bytes, media_type=media_type)


@router.post(
    "/preview/script",
    summary="Preview de gráfico a partir de script matplotlib",
    response_class=Response,
)
async def preview_script(
    code: str,
    rows: list[dict[str, Any]],
    output_format: Literal["png", "svg"] = "png",
    sandbox: SandboxClient = Depends(get_sandbox_client),
) -> Response:
    """Audita y ejecuta un script matplotlib; devuelve bytes de imagen.

    No persiste nada. El script recibe `df` (pandas DataFrame) ya cargado.
    """
    if not rows:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="rows cannot be empty")

    df = pd.DataFrame(rows)
    try:
        image_bytes = await render_chart_from_script(
            code, df, output_format=output_format, sandbox_client=sandbox
        )
    except ChartRenderError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    media_type = "image/svg+xml" if output_format == "svg" else "image/png"
    return Response(content=image_bytes, media_type=media_type)
