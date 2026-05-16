"""Motor ETL determinista + modo IA — 9R.5.8.

Migrado y refactorizado desde client_app/app/services/etl_service.py:
  - Catálogo declarativo de operaciones (Pydantic discriminated union).
  - Engine determinista in-memory sobre pandas.
  - ETLFactory: NL → list[Operation] con refinamiento iterativo (MAX=3) y
    fallback a script Python auditado cuando las operaciones no encajan.
  - ETLService: orquestador async que envuelve ambos modos.
"""
from server.app.modules.redaccion.services.transformation.operations import (
    AggregateOp,
    FilterOp,
    GroupByOp,
    JoinOp,
    NormalizeOp,
    Operation,
    PivotOp,
    parse_operations,
)
from server.app.modules.redaccion.services.transformation.deterministic_etl import (
    DeterministicETLService,
    UnknownOperationError,
)
from server.app.modules.redaccion.services.transformation.etl_factory import (
    ETLFactory,
    ETLPlan,
    MAX_REFINEMENT_ITERATIONS,
)
from server.app.modules.redaccion.services.transformation.etl_service import (
    ETLService,
    ETLServiceResult,
)

__all__ = [
    "AggregateOp",
    "FilterOp",
    "GroupByOp",
    "JoinOp",
    "NormalizeOp",
    "Operation",
    "PivotOp",
    "parse_operations",
    "DeterministicETLService",
    "UnknownOperationError",
    "ETLFactory",
    "ETLPlan",
    "MAX_REFINEMENT_ITERATIONS",
    "ETLService",
    "ETLServiceResult",
]
