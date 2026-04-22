"""
PreviewDataService - Servicio para previsualización de datos en diseño de flujos.

Permite obtener una muestra representativa de datos de:
1. Un paso anterior del flujo (ejecutándolo realmente)
2. Un átomo del catálogo (sample_data o mock desde output_contract)

Este servicio es clave para eliminar la "configuración a ciegas" en el diseño de flujos.
"""
import json
import time
import asyncio
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd


# TTL de caché en segundos (5 minutos)
_CACHE_TTL_SECONDS = 300

# Caché en memoria: key → (timestamp, PreviewResult)
_preview_cache: Dict[str, Tuple[float, "PreviewResult"]] = {}


# ============================================================================
# DATACLASSES DE RESULTADO
# ============================================================================

@dataclass
class PreviewResult:
    """Encapsula el resultado de una solicitud de previsualización de datos."""
    success: bool
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0           # Filas reales del resultado completo (estimado)
    preview_rows: int = 0        # Filas incluidas en este preview
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    source_type: str = "unknown"  # 'executed_step' | 'sample_data' | 'mock_data'
    is_real_execution: bool = False  # True si se ejecutó código real

    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """Convierte las filas en un DataFrame de pandas."""
        if not self.rows:
            return None
        return pd.DataFrame(self.rows, columns=self.columns or None)


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================

class PreviewDataService:
    """
    Servicio para obtener previsualizaciones de datos en el contexto de diseño de flujos.

    Diseñado para ser invocado desde el DataSourceSelector cuando el usuario
    quiere ver los datos que producirá un paso anterior o un átomo del catálogo.
    """

    # ──────────────────────────────────────────────────────────
    # CACHÉ
    # ──────────────────────────────────────────────────────────

    def _cache_key(self, prefix: str, *parts) -> str:
        return f"{prefix}:" + ":".join(str(p) for p in parts)

    def _cache_get(self, key: str) -> Optional["PreviewResult"]:
        """Devuelve el resultado cacheado si existe y no expiró."""
        entry = _preview_cache.get(key)
        if entry is None:
            return None
        timestamp, result = entry
        if time.monotonic() - timestamp > _CACHE_TTL_SECONDS:
            del _preview_cache[key]
            return None
        return result

    def _cache_set(self, key: str, result: "PreviewResult") -> None:
        """Guarda un resultado en caché."""
        _preview_cache[key] = (time.monotonic(), result)

    def invalidate_flow_cache(self, flow_id: int) -> None:
        """Invalida todas las entradas de caché de un flujo específico."""
        keys_to_remove = [k for k in _preview_cache if k.startswith(f"step:{flow_id}:")]
        for k in keys_to_remove:
            del _preview_cache[k]

    # ──────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL: Preview desde paso anterior
    # ──────────────────────────────────────────────────────────

    async def get_preview_from_previous_step(
        self,
        flow_id: int,
        source_step_index: int,
        all_steps_config: List[Dict[str, Any]],
        max_rows: int = 15,
        timeout_seconds: float = 30.0
    ) -> PreviewResult:
        """
        Ejecuta el paso fuente y retorna un preview de sus datos.

        ADVERTENCIA: Este método ejecuta código real del usuario (llamadas a APIs,
        queries a base de datos, etc.) con los parámetros configurados en el paso.

        Args:
            flow_id: ID del flujo (usado para caché)
            source_step_index: Índice del paso del que queremos datos
            all_steps_config: Lista de configuraciones de pasos del flujo
            max_rows: Máximo de filas en el preview
            timeout_seconds: Tiempo máximo de ejecución

        Returns:
            PreviewResult con los datos del paso o un error descriptivo
        """
        cache_key = self._cache_key("step", flow_id, source_step_index)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Obtener la configuración del paso fuente
        if source_step_index >= len(all_steps_config):
            return PreviewResult(
                success=False,
                error=f"Paso {source_step_index + 1} no encontrado en la configuración del flujo."
            )

        step_config = all_steps_config[source_step_index]
        step_type = step_config.get("type", "unknown")

        try:
            result = await asyncio.wait_for(
                self._execute_step_for_preview(step_config, all_steps_config, source_step_index, max_rows),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            result = PreviewResult(
                success=False,
                error=f"Tiempo de espera agotado ({timeout_seconds}s) al ejecutar el paso '{step_config.get('name', step_type)}'. "
                      f"El paso puede requerir una conexión lenta. Intenta reduciendo los datos o usando datos de ejemplo."
            )
        except Exception as ex:
            result = PreviewResult(
                success=False,
                error=f"Error al ejecutar el paso '{step_config.get('name', step_type)}': {str(ex)}"
            )

        if result.success:
            self._cache_set(cache_key, result)

        return result

    async def _execute_step_for_preview(
        self,
        step_config: Dict[str, Any],
        all_steps_config: List[Dict[str, Any]],
        step_index: int,
        max_rows: int
    ) -> PreviewResult:
        """
        Ejecuta secuencialmente los pasos previos para obtener los datos de ENTRADA
        al paso step_index.

        Semántica:
        - Para step_index=0: ejecuta paso 0 y retorna su output (es el primer paso)
        - Para step_index>0: ejecuta pasos 0 hasta step_index-1 y retorna el output
          del último, que son los datos de entrada al paso step_index.

        Esto permite previsualizar qué datos recibirá un paso antes de configurarlo.
        """
        from automatia_shared.dtos import TaskSpec
        from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
        from client_app.app.database.db import get_db

        async with get_db() as session:
            engine = WorkflowEngine(session)
            previous_output = None

            # Determinar hasta qué paso ejecutar:
            # - Para paso 0: ejecutar solo paso 0 (no hay paso previo)
            # - Para paso N: ejecutar pasos 0..N-1 para obtener datos de entrada a N
            last_step_to_execute = step_index if step_index == 0 else step_index - 1

            for idx in range(last_step_to_execute + 1):
                current_step = all_steps_config[idx]
                step_type = current_step.get("type", "")
                step_name = current_step.get("name", f"Paso {idx + 1}")

                task = TaskSpec(
                    id=idx,
                    name=step_name,
                    type=step_type,
                    config=current_step.get("config", {}),
                )

                context: Dict[str, Any] = {
                    "previous_output": previous_output,
                    "step_index": idx,
                    "preview_mode": True,
                }

                try:
                    raw_output = await engine._execute_task(task, context)
                    previous_output = raw_output
                except Exception as e:
                    raise ValueError(
                        f"Fallo en paso '{step_name}' (paso {idx + 1}): {str(e)}"
                    )

            # Normalizar el output para visualización
            output_step_type = all_steps_config[last_step_to_execute].get("type", "")
            return self._normalize_output_to_preview(previous_output, output_step_type, max_rows)

    def _normalize_output_to_preview(
        self,
        raw_output: Any,
        step_type: str,
        max_rows: int
    ) -> PreviewResult:
        """
        Convierte el output de cualquier tipo de paso en un PreviewResult tabular.
        """
        if raw_output is None:
            return PreviewResult(
                success=True,
                source_type="executed_step",
                is_real_execution=True,
                metadata={"note": "El paso no retornó datos (output=None)", "step_type": step_type}
            )

        # DataFrame de pandas
        if isinstance(raw_output, pd.DataFrame):
            rows_total = len(raw_output)
            preview_df = raw_output.head(max_rows)
            # Convertir tipos no-serializables
            preview_df = preview_df.fillna("").astype(str)
            columns = list(preview_df.columns)
            rows = preview_df.to_dict(orient="records")
            return PreviewResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=rows_total,
                preview_rows=len(rows),
                source_type="executed_step",
                is_real_execution=True,
                metadata={"step_type": step_type, "dtypes": str(raw_output.dtypes.to_dict())}
            )

        # Lista de dicts (ej: folder_scan, email_scan)
        if isinstance(raw_output, list):
            rows_total = len(raw_output)
            preview_items = raw_output[:max_rows]
            if preview_items and isinstance(preview_items[0], dict):
                columns = list(preview_items[0].keys())
                rows = [self._serialize_dict(item) for item in preview_items]
            else:
                # Lista de primitivos
                columns = ["value"]
                rows = [{"value": str(item)} for item in preview_items]
            return PreviewResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=rows_total,
                preview_rows=len(rows),
                source_type="executed_step",
                is_real_execution=True,
                metadata={"step_type": step_type}
            )

        # Diccionario (ej: api_fetch, extraction)
        if isinstance(raw_output, dict):
            # Buscar la mejor lista recursivamente (data, records, items, etc.)
            best_list, extracted_path = self._find_best_list(raw_output)
            
            if best_list:
                rows_total = len(best_list)
                preview_items = best_list[:max_rows]
                columns = list(preview_items[0].keys())
                rows = [self._serialize_dict(item) for item in preview_items]
                return PreviewResult(
                    success=True,
                    columns=columns,
                    rows=rows,
                    row_count=rows_total,
                    preview_rows=len(rows),
                    source_type="executed_step",
                    is_real_execution=True,
                    metadata={"step_type": step_type, "extracted_from_path": extracted_path}
                )
            
            # Si no hay listas explícitas devolvemos el dict mismo como un registro
            # Check simple de si es un dict "plano" asumimos que es 1 registro
            is_flat = all(not isinstance(v, (list, dict)) for v in raw_output.values())
            if is_flat and raw_output:
                serialized = self._serialize_dict(raw_output)
                return PreviewResult(
                    success=True,
                    columns=list(serialized.keys()),
                    rows=[serialized],
                    row_count=1,
                    preview_rows=1,
                    source_type="executed_step",
                    is_real_execution=True,
                    metadata={"step_type": step_type, "format": "single_record"}
                )

            # Mostrar como tabla clave-valor paramétricamente general
            serialized = self._serialize_dict(raw_output)
            columns = ["campo", "valor"]
            rows = [{"campo": k, "valor": str(v)} for k, v in serialized.items()][:max_rows]
            return PreviewResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(raw_output),
                preview_rows=len(rows),
                source_type="executed_step",
                is_real_execution=True,
                metadata={"step_type": step_type, "format": "key-value"}
            )

        # Tipos simples
        return PreviewResult(
            success=True,
            columns=["resultado"],
            rows=[{"resultado": str(raw_output)}],
            row_count=1,
            preview_rows=1,
            source_type="executed_step",
            is_real_execution=True,
            metadata={"step_type": step_type, "raw_type": type(raw_output).__name__}
        )

    # ──────────────────────────────────────────────────────────
    # MÉTODO: Preview desde átomo del catálogo
    # ──────────────────────────────────────────────────────────

    async def get_preview_from_atom(
        self,
        atom_id: int,
        max_rows: int = 15
    ) -> PreviewResult:
        """
        Obtiene datos de ejemplo de un átomo del catálogo.

        Estrategia (en orden de prioridad):
        1. Campo `sample_data` del AtomRegistry (datos reales cacheados)
        2. Datos mock generados desde `output_contract`

        Args:
            atom_id: ID del átomo en AtomRegistry
            max_rows: Máximo de filas a retornar

        Returns:
            PreviewResult con datos de ejemplo o mock
        """
        cache_key = self._cache_key("atom", atom_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        from client_app.app.services.atom_service import atom_service

        atom = await atom_service.get_atom(atom_id)
        if atom is None:
            return PreviewResult(
                success=False,
                error=f"Acción con ID {atom_id} no encontrada en el catálogo."
            )

        # Obtener step_type del átomo para incluirlo en metadata
        atom_step_type = getattr(atom, "atom_type", None)
        if hasattr(atom_step_type, "value"):
            atom_step_type = atom_step_type.value
        atom_step_type = str(atom_step_type) if atom_step_type else ""

        # Prioridad 1: sample_data del átomo
        sample_data_raw = getattr(atom, "sample_data", None)
        if sample_data_raw:
            try:
                sample = json.loads(sample_data_raw)
                rows = sample.get("rows", [])
                columns = sample.get("columns", list(rows[0].keys()) if rows else [])
                preview_rows = rows[:max_rows]
                result = PreviewResult(
                    success=True,
                    columns=columns,
                    rows=preview_rows,
                    row_count=len(rows),
                    preview_rows=len(preview_rows),
                    source_type="sample_data",
                    is_real_execution=False,
                    metadata={
                        "atom_name": atom.name,
                        "step_type": atom_step_type,
                        "generated_at": sample.get("generated_at", "desconocido"),
                        "source": sample.get("source", "desconocido")
                    }
                )
                self._cache_set(cache_key, result)
                return result
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"[PreviewDataService] Error parsing sample_data for atom {atom_id}: {e}")

        # Prioridad 2: Mock desde output_contract
        output_contract_raw = getattr(atom, "output_contract", None)
        if output_contract_raw:
            try:
                contract = json.loads(output_contract_raw)
                result = await self.generate_mock_from_contract(contract, num_rows=min(max_rows, 5))
                result.metadata["atom_name"] = atom.name
                result.metadata["step_type"] = atom_step_type
                self._cache_set(cache_key, result)
                return result
            except (json.JSONDecodeError, Exception) as e:
                print(f"[PreviewDataService] Error generating mock from contract for atom {atom_id}: {e}")

        # Fallback: sin datos
        return PreviewResult(
            success=True,
            source_type="mock_data",
            is_real_execution=False,
            metadata={
                "atom_name": atom.name,
                "step_type": atom_step_type,
                "note": "Esta acción no tiene datos de ejemplo configurados ni contrato de salida definido."
            }
        )

    # ──────────────────────────────────────────────────────────
    # MÉTODO: Ejecutar átomo del catálogo para obtener datos reales
    # ──────────────────────────────────────────────────────────

    async def execute_atom_for_preview(
        self,
        atom_id: int,
        max_rows: int = 15,
        timeout_seconds: float = 30.0
    ) -> PreviewResult:
        """
        Ejecuta un átomo del catálogo y retorna sus datos reales.

        Especialmente útil para átomos de tipo folder_scan, email_scan, etc.
        que necesitan ejecutarse para obtener la lista de archivos.

        Args:
            atom_id: ID del átomo en AtomRegistry
            max_rows: Máximo de filas a retornar
            timeout_seconds: Tiempo máximo de ejecución

        Returns:
            PreviewResult con datos reales del átomo ejecutado
        """
        from client_app.app.services.atom_service import atom_service
        from automatia_shared.dtos import TaskSpec
        from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
        from client_app.app.database.db import get_db

        atom = await atom_service.get_atom(atom_id)
        if atom is None:
            return PreviewResult(
                success=False,
                error=f"Acción con ID {atom_id} no encontrada en el catálogo."
            )

        # Obtener step_type del átomo
        atom_step_type = getattr(atom, "atom_type", None)
        if hasattr(atom_step_type, "value"):
            atom_step_type = atom_step_type.value
        atom_step_type = str(atom_step_type) if atom_step_type else ""

        # Construir configuración del paso desde el átomo
        try:
            default_config = json.loads(getattr(atom, "default_config", "{}") or "{}")
        except json.JSONDecodeError:
            default_config = {}

        step_config = {
            "type": atom_step_type,
            "name": atom.name,
            "config": default_config
        }

        try:
            async with get_db() as session:
                engine = WorkflowEngine(session)

                # Crear TaskSpec para el paso
                task = TaskSpec(
                    id=0,
                    type=atom_step_type,
                    name=atom.name,
                    config=default_config
                )

                # Contexto de ejecución
                context = {
                    "previous_output": None,
                    "step_index": 0,
                    "preview_mode": True,
                }

                # Ejecutar el paso
                raw_output = await asyncio.wait_for(
                    engine._execute_task(task, context),
                    timeout=timeout_seconds
                )

                # Procesar el resultado usando el normalizador existente
                result = self._normalize_output_to_preview(raw_output, atom_step_type, max_rows)
                result.metadata["atom_name"] = atom.name
                result.metadata["atom_id"] = atom_id
                return result

        except asyncio.TimeoutError:
            return PreviewResult(
                success=False,
                error=f"Tiempo de espera agotado ({timeout_seconds}s) al ejecutar '{atom.name}'. "
                      f"La acción puede requerir acceso a recursos lentos."
            )
        except Exception as ex:
            return PreviewResult(
                success=False,
                error=f"Error al ejecutar '{atom.name}': {str(ex)}",
                metadata={"step_type": atom_step_type, "atom_name": atom.name}
            )

    # ──────────────────────────────────────────────────────────
    # MÉTODO: Generación de datos mock desde contrato
    # ──────────────────────────────────────────────────────────

    async def generate_mock_from_contract(
        self,
        output_contract: Dict[str, Any],
        num_rows: int = 5
    ) -> PreviewResult:
        """
        Genera datos mock representativos basados en el contrato de salida.

        Soporta contratos JSON Schema con campos 'properties'.

        Args:
            output_contract: Dict con la definición del contrato (JSON Schema)
            num_rows: Número de filas de ejemplo a generar

        Returns:
            PreviewResult con datos mock
        """
        properties = output_contract.get("properties", {})

        if not properties:
            # Intentar formato alternativo plano: {campo: tipo}
            # Formato usado en algunos contratos del proyecto
            alt_props = {
                k: {"type": v} if isinstance(v, str) else v
                for k, v in output_contract.items()
                if k not in ("type", "title", "description", "required", "$schema")
            }
            if alt_props:
                properties = alt_props

        if not properties:
            return PreviewResult(
                success=True,
                source_type="mock_data",
                is_real_execution=False,
                metadata={"note": "Contrato sin propiedades definidas"}
            )

        columns = list(properties.keys())
        rows = []
        today_str = date.today().isoformat()

        for row_idx in range(num_rows):
            row = {}
            for col, schema in properties.items():
                col_type = schema.get("type", "string") if isinstance(schema, dict) else "string"
                row[col] = self._generate_mock_value(col, col_type, row_idx, today_str)
            rows.append(row)

        return PreviewResult(
            success=True,
            columns=columns,
            rows=rows,
            row_count=num_rows,
            preview_rows=num_rows,
            source_type="mock_data",
            is_real_execution=False,
            metadata={"note": "Datos de ejemplo generados automáticamente desde el contrato de salida"}
        )

    def _generate_mock_value(self, field_name: str, field_type: str, row_idx: int, today_str: str) -> Any:
        """Genera un valor de ejemplo para un campo según su tipo."""
        name_lower = field_name.lower()

        # Heurísticas por nombre de campo
        if "email" in name_lower:
            return f"usuario{row_idx + 1}@ejemplo.com"
        if "nombre" in name_lower or "name" in name_lower:
            nombres = ["Ana García", "Carlos López", "María Martínez", "Pedro Sánchez", "Laura Fernández"]
            return nombres[row_idx % len(nombres)]
        if "fecha" in name_lower or "date" in name_lower:
            return today_str
        if "precio" in name_lower or "price" in name_lower or "amount" in name_lower or "importe" in name_lower:
            return round(random.uniform(10.0, 1000.0), 2)
        if "id" in name_lower:
            return row_idx + 1

        # Por tipo de dato
        if field_type in ("integer", "int"):
            return random.randint(1, 1000)
        if field_type in ("number", "float"):
            return round(random.uniform(0.0, 100.0), 2)
        if field_type == "boolean":
            return row_idx % 2 == 0
        if field_type in ("date", "date-time"):
            return today_str
        if field_type == "array":
            return []
        if field_type == "object":
            return {}

        # Por defecto: string descriptivo
        return f"Ejemplo de {field_name} {row_idx + 1}"

    # ──────────────────────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────────────────────

    def _find_best_list(self, data: Any, depth: int = 0) -> Tuple[Optional[List], Optional[str]]:
        """
        Busca recursivamente la lista "más rica" de diccionarios en un objeto JSON.
        Retorna (lista, path_de_extraccion).
        """
        if depth > 5: # Un poco más de margen para niveles anidados
            return None, None
            
        if isinstance(data, list):
            # Si es una lista de un solo elemento y ese elemento es un dict, 
            # posiblemente la data real esté dentro de ese dict (ej: wrapper de API)
            if len(data) == 1 and isinstance(data[0], dict):
                inner_list, inner_path = self._find_best_list(data[0], depth + 1)
                if inner_list:
                    return inner_list, f"0.{inner_path}".strip(".")

            if data and isinstance(data[0], dict):
                return data, ""
            return None, None
            
        if isinstance(data, dict):
            # Prioridad a claves comunes de colecciones reales (añadido 'result' y 'results')
            priority_keys = ["records", "data", "items", "rows", "results", "result", "value"]
            for key in priority_keys:
                if key in data:
                    res_list, res_path = self._find_best_list(data[key], depth + 1)
                    if res_list:
                        return res_list, f"{key}.{res_path}".strip(".")
            
            # Si no hay prioridad, buscar en todas las llaves (eligiendo la lista más larga)
            best_list = None
            best_path = None
            max_len = -1
            
            for key, val in data.items():
                if key == "help": continue # Metadata CKAN que suele ser string largo
                res_list, res_path = self._find_best_list(val, depth + 1)
                if res_list and len(res_list) > max_len:
                    best_list = res_list
                    best_path = f"{key}.{res_path}".strip(".")
                    max_len = len(res_list)
            
            return best_list, best_path
            
        return None, None

    def _serialize_dict(self, d: Dict) -> Dict:
        """Convierte un diccionario a formato JSON-serializable (strings)."""
        result = {}
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                result[k] = json.dumps(v, ensure_ascii=False, default=str)
            elif isinstance(v, (datetime, date)):
                result[k] = v.isoformat()
            elif v is None:
                result[k] = ""
            else:
                result[k] = str(v)
        return result


# ============================================================================
# SINGLETON
# ============================================================================

preview_data_service = PreviewDataService()
