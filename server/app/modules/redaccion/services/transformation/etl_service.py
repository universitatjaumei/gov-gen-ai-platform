"""ETLService — orquestador asíncrono que envuelve los dos modos del módulo (9R.5.8).

Capa fina sobre `DeterministicETLService` y `ETLFactory`. La invoca tanto el
`DataTransformHandler` (bloque DATA_TRANSFORM) como cualquier consumidor que
necesite aplicar transformaciones sobre un DataFrame ya en memoria.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from server.app.modules.redaccion.services.transformation.deterministic_etl import (
    DeterministicETLService,
    JoinableResolver,
)
from server.app.modules.redaccion.services.transformation.etl_factory import (
    ETLFactory,
    ETLPlan,
)
from server.app.modules.redaccion.services.transformation.operations import Operation


@dataclass
class ETLServiceResult:
    dataframe: pd.DataFrame
    operations_applied: list[Operation] = field(default_factory=list)
    model_used: str | None = None
    plan: ETLPlan | None = None  # solo en modo ai


class ETLService:
    """Aplica transformaciones (deterministic o ai) sobre un DataFrame."""

    def __init__(self, llm: Any = None, model_name: str = "") -> None:
        self._llm = llm
        self._model_name = model_name

    async def run(
        self,
        *,
        df: pd.DataFrame,
        mode: Literal["deterministic", "ai"],
        operations: list[Operation] | None = None,
        nl_instruction: str | None = None,
        joinable_resolver: JoinableResolver | None = None,
    ) -> ETLServiceResult:
        engine = DeterministicETLService(joinable_resolver=joinable_resolver)

        if mode == "deterministic":
            if not operations:
                raise ValueError("operations list is required in deterministic mode")
            transformed = engine.execute(df, operations)
            return ETLServiceResult(
                dataframe=transformed,
                operations_applied=list(operations),
                model_used=None,
            )

        # AI mode
        if self._llm is None:
            raise ValueError("ai mode requires an injected llm")
        if not nl_instruction:
            raise ValueError("nl_instruction is required in ai mode")

        factory = ETLFactory(self._llm, model_name=self._model_name)
        schema = self._schema_of(df)
        plan = await factory.generate_operations_from_nl(nl_instruction, schema)

        if plan.mode == "operations":
            transformed = engine.execute(df, plan.operations)
            return ETLServiceResult(
                dataframe=transformed,
                operations_applied=list(plan.operations),
                model_used=plan.model_used or self._model_name,
                plan=plan,
            )

        # Script fallback: solo se ejecuta si la auditoría lo aprueba.
        if not (plan.script_audit and plan.script_audit.approved):
            raise ValueError(
                "Script de fallback rechazado por la auditoría: "
                f"{plan.script_audit.findings if plan.script_audit else 'sin auditoría'}"
            )
        transformed = self._execute_fallback_script(plan.script_code or "", df)
        return ETLServiceResult(
            dataframe=transformed,
            operations_applied=[],
            model_used=plan.model_used or self._model_name,
            plan=plan,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _schema_of(df: pd.DataFrame) -> dict[str, Any]:
        return {
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        }

    @staticmethod
    def _execute_fallback_script(code: str, df: pd.DataFrame) -> pd.DataFrame:
        """Ejecuta el script en un namespace local controlado.

        El AST ya ha sido auditado por `ScriptSecurityAuditor` antes de
        llegar aquí (sin acceso a builtins peligrosos ni a módulos fuera
        de la lista blanca). Para el MVP basta `exec` directo;
        si emergen requisitos de aislamiento más fuertes, migrar a un
        subprocess sandbox análogo al ChartRenderer.
        """
        namespace: dict[str, Any] = {"pd": pd, "df": df.copy()}
        exec(compile(code, "<etl-fallback>", "exec"), namespace)
        transform = namespace.get("transform")
        if not callable(transform):
            raise ValueError("Fallback script must define a `transform(df)` function")
        return transform(df.copy())
