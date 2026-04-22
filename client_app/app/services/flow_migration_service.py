"""
Flow Migration Service - Migración de flujos existentes al nuevo sistema de átomos.
Prompt 6.1 del plan de refactorización del editor de flujos.

Proporciona funcionalidad para migrar flujos del formato legacy (JSON embebido)
al nuevo sistema basado en FlowStep con referencias a AtomRegistry.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import FlowRegistry, AtomRegistry, FlowStep
from automatia_shared.enums import StepType


@dataclass
class MigrationStatus:
    """Estado de la migración de flujos."""
    total_flows: int
    migrated_flows: int
    pending_flows: int

    @property
    def is_complete(self) -> bool:
        """True si todos los flujos están migrados."""
        return self.pending_flows == 0

    @property
    def progress_percentage(self) -> float:
        """Porcentaje de progreso de la migración."""
        if self.total_flows == 0:
            return 100.0
        return (self.migrated_flows / self.total_flows) * 100


class FlowMigrationService:
    """
    Servicio para migración de flujos del formato legacy al nuevo sistema.

    Implementa patrón Singleton para asegurar una única instancia.
    """
    _instance = None

    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _parse_steps_json(self, steps_str: str) -> List[Dict[str, Any]]:
        """Parsea el JSON de steps del formato legacy."""
        try:
            if not steps_str or steps_str.strip() == "":
                return []
            steps = json.loads(steps_str)
            return steps if isinstance(steps, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _step_type_from_string(self, type_str: str) -> Optional[StepType]:
        """Convierte string de tipo a StepType enum."""
        try:
            # Intentar primero con el valor directo
            return StepType(type_str)
        except ValueError:
            # Intentar con el nombre en mayúsculas
            try:
                return StepType[type_str.upper()]
            except KeyError:
                return None

    def _generate_config_schema(self, step_type: StepType) -> str:
        """Genera un JSON Schema básico para el tipo de paso."""
        schemas = {
            StepType.API_FETCH: {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL del endpoint"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                    "headers": {"type": "object"},
                    "body": {"type": "string"}
                },
                "required": ["url"]
            },
            StepType.EMAIL_SEND: {
                "type": "object",
                "properties": {
                    "recipients": {"type": "string", "description": "Destinatarios"},
                    "subject": {"type": "string", "description": "Asunto"},
                    "body": {"type": "string", "description": "Cuerpo del email"}
                },
                "required": ["recipients", "subject"]
            },
            StepType.EXTRACTION: {
                "type": "object",
                "properties": {
                    "config_id": {"type": "string", "description": "ID de configuración de extracción"}
                },
                "required": ["config_id"]
            },
            StepType.CUSTOM_SCRIPT: {
                "type": "object",
                "properties": {
                    "script_id": {"type": "string", "description": "ID del script a ejecutar"}
                },
                "required": ["script_id"]
            },
            StepType.NAVIGATION: {
                "type": "object",
                "properties": {
                    "playbook_id": {"type": "integer", "description": "ID del playbook de navegación"}
                },
                "required": ["playbook_id"]
            }
        }
        schema = schemas.get(step_type, {"type": "object", "properties": {}})
        return json.dumps(schema)

    async def _find_or_create_atom(
        self,
        session: AsyncSession,
        step_type: StepType,
        step_name: str
    ) -> AtomRegistry:
        """
        Busca un átomo existente del tipo especificado o crea uno nuevo.

        Args:
            session: Sesión de base de datos
            step_type: Tipo del paso
            step_name: Nombre del paso (para crear átomo si no existe)

        Returns:
            AtomRegistry existente o nuevo
        """
        # Buscar átomo existente del mismo tipo
        query = select(AtomRegistry).where(
            AtomRegistry.atom_type == step_type,
            AtomRegistry.is_active == True
        ).limit(1)

        result = await session.execute(query)
        existing_atom = result.scalars().first()

        if existing_atom:
            return existing_atom

        # No existe, crear átomo genérico para el tipo
        atom = AtomRegistry(
            name=f"{step_type.value.replace('_', ' ').title()} (Migrado)",
            atom_type=step_type,
            description=f"Átomo genérico para {step_type.value} creado por migración",
            config_schema=self._generate_config_schema(step_type),
            default_config="{}",
            version="1.0.0",
            is_active=True
        )

        session.add(atom)
        await session.commit()
        await session.refresh(atom)

        return atom

    async def _has_existing_flow_steps(
        self,
        session: AsyncSession,
        flow_id: int
    ) -> bool:
        """Verifica si un flujo ya tiene FlowSteps (ya migrado)."""
        query = select(FlowStep).where(FlowStep.flow_id == flow_id).limit(1)
        result = await session.execute(query)
        return result.scalars().first() is not None

    async def migrate_flow(self, flow_id: int) -> bool:
        """
        Migra un flujo individual del formato legacy (JSON de pasos embebido)
        al nuevo sistema basado en átomos y pasos persistidos independientemente.

        Args:
            flow_id: ID del flujo a migrar.

        Returns:
            True si la migración fue exitosa o si el flujo ya estaba migrado.
        """
        async with AsyncSession(client_engine) as session:
            # Obtener el flujo
            flow = await session.get(FlowRegistry, flow_id)
            if not flow:
                return False

            # Verificar si ya está migrado
            if await self._has_existing_flow_steps(session, flow_id):
                # Ya está migrado, es idempotente
                return True

            # Parsear steps legacy
            legacy_steps = self._parse_steps_json(flow.steps)

            if not legacy_steps:
                # Flujo vacío, marcar como migrado y retornar
                return True

            # Migrar cada paso
            for idx, step_data in enumerate(legacy_steps):
                step_name = step_data.get("name", f"Paso {idx + 1}")
                step_type_str = step_data.get("type", "")
                step_config = step_data.get("config", {})

                # Convertir tipo
                step_type = self._step_type_from_string(step_type_str)
                if not step_type:
                    # Tipo desconocido, usar CUSTOM_SCRIPT como fallback
                    step_type = StepType.CUSTOM_SCRIPT

                # Buscar o crear átomo
                atom = await self._find_or_create_atom(session, step_type, step_name)

                # Crear FlowStep
                flow_step = FlowStep(
                    flow_id=flow_id,
                    atom_id=atom.id,
                    step_order=idx,
                    custom_name=step_name,
                    custom_config=json.dumps(step_config) if step_config else None,
                    output_var_name=f"result_step_{idx}"
                )

                session.add(flow_step)

            # Commit todos los cambios
            await session.commit()

            return True

    async def migrate_all_flows(self) -> Dict[int, bool]:
        """
        Orquesta la migración masiva de todos los flujos activos en el sistema.

        Returns:
            Diccionario que mapea IDs de flujos con el resultado de su migración.
        """
        async with AsyncSession(client_engine) as session:
            # Obtener todos los flujos activos
            query = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(query)
            flows = result.scalars().all()

        # Migrar cada flujo
        results = {}
        for flow in flows:
            try:
                success = await self.migrate_flow(flow.id)
                results[flow.id] = success
            except Exception:
                results[flow.id] = False

        return results

    async def check_migration_status(self) -> MigrationStatus:
        """
        Verifica el estado actual de la migración.

        Returns:
            MigrationStatus: Estado con conteos de flujos migrados/pendientes
        """
        async with AsyncSession(client_engine) as session:
            # Total de flujos activos
            query_total = select(func.count()).select_from(FlowRegistry).where(
                FlowRegistry.is_active == True
            )
            result_total = await session.execute(query_total)
            total_flows = result_total.scalar() or 0

            # Flujos con FlowSteps (migrados)
            # Subconsulta para obtener flow_ids con FlowSteps
            subquery = select(FlowStep.flow_id).distinct()
            query_migrated = select(func.count()).select_from(FlowRegistry).where(
                FlowRegistry.is_active == True,
                FlowRegistry.id.in_(subquery)
            )
            result_migrated = await session.execute(query_migrated)
            migrated_flows = result_migrated.scalar() or 0

            pending_flows = total_flows - migrated_flows

        return MigrationStatus(
            total_flows=total_flows,
            migrated_flows=migrated_flows,
            pending_flows=pending_flows
        )


# Singleton Instance
flow_migration_service = FlowMigrationService()
