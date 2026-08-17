"""Cómo se le enseña a un modelo un contrato Pydantic sin copiarlo a mano.

PRO.4 lo hizo para las operaciones de ETL y PRO.8 lo necesita igual para la configuración de
gráfico, así que vive aquí en vez de duplicado: **un catálogo escrito a mano en un prompt
diverge del contrato en el primer cambio**, y el síntoma es un modelo que no usa la mitad de lo
que existe sin que nadie sepa por qué.
"""
from __future__ import annotations

import types
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel


def tipo_legible(anotacion: Any) -> str:
    """Los valores admitidos si el tipo es cerrado, y el nombre del tipo si no."""
    origen = get_origin(anotacion)
    if origen is Literal:
        return "|".join(str(v) for v in get_args(anotacion))
    # `Optional[x]` y `x | None` son la misma cosa con dos orígenes distintos: sin las dos, el
    # catálogo le enseña al modelo `list[str] | None` en vez de `[str]`.
    if origen is Union or origen is types.UnionType:
        partes = [a for a in get_args(anotacion) if a is not type(None)]
        return "|".join(tipo_legible(p) for p in partes)
    if origen in (list, set):
        interno = get_args(anotacion)
        return f"[{tipo_legible(interno[0])}]" if interno else "[]"
    if origen is tuple:
        return "[number, number]"
    if origen is dict:
        return "{...}"
    return getattr(anotacion, "__name__", str(anotacion))


def campos_legibles(
    modelo: type[BaseModel], omitir: tuple[str, ...] = ()
) -> list[str]:
    """Una línea `"campo": tipo (defecto)` por cada campo del modelo."""
    lineas: list[str] = []
    for nombre, campo in modelo.model_fields.items():
        if nombre in omitir:
            continue
        linea = f'  "{nombre}": {tipo_legible(campo.annotation)}'
        if campo.default is not None and campo.default is not ...:
            linea += f"   (por defecto: {campo.default!r})"
        lineas.append(linea)
    return lineas
