import json
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from client_app.app.database.models import FlowRegistry, ETLJobHistory
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import TaskStatus
from datetime import datetime
from client_app.app.database.db import client_engine
from sqlalchemy.ext.asyncio import AsyncSession
from client_app.app.services.trigger_lifecycle_manager import trigger_lifecycle_manager
from client_app.app.database.models import TriggerConfig

class OptimisticLockError(Exception):
    """Excepción lanzada cuando falla el bloqueo optimista (discrepancia en row_version)."""
    pass

class FlowRegistryService:
    """
    Servicio para la gestión del ciclo de vida de los flujos de automatización.
    Maneja el almacenamiento, recuperación, actualización (con bloqueo optimista)
    y eliminación de flujos en la base de datos local.
    """
    def __init__(self, session: AsyncSession = None):
        self.session = session

    async def list_flows(
        self,
        status: Optional[str] = None,
        owner_scope: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[FlowRegistry]:
        """
        Lista los flujos con filtrado opcional.

        Args:
            status: Estado del flujo (DRAFT, PUBLISHED, etc.).
            owner_scope: Ámbito del propietario (user, department, etc.).
            skip: Número de registros a omitir (paginación).
            limit: Número máximo de registros a retornar.

        Returns:
            Lista de objetos FlowRegistry.
        """
        query = select(FlowRegistry)
        
        if status:
            query = query.where(FlowRegistry.status == status)
        
        if owner_scope:
            query = query.where(FlowRegistry.owner_scope == owner_scope)
            
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_flow(self, flow_id: int) -> Optional[FlowRegistry]:
        """
        Obtiene un flujo por su ID único.

        Args:
            flow_id: ID numérico del flujo.

        Returns:
            El objeto FlowRegistry o None si no se encuentra.
        """
        return await self.session.get(FlowRegistry, flow_id)

    async def get_flow_spec(self, flow_id: int) -> Optional[FlowSpec]:
        """
        Retrieves the FlowSpec for a given flow ID.
        """
        flow = await self.get_flow(flow_id)
        if not flow:
            return None
        return self._to_spec(flow)

    async def get_flow_history(self, name: str) -> List[FlowRegistry]:
        """
        Recupera todas las versiones de un flujo por su nombre.

        Args:
            name: Nombre del flujo (todas las versiones comparten el mismo nombre).

        Returns:
            Lista de FlowRegistry ordenada por fecha de creación (más reciente primero).
        """
        query = (
            select(FlowRegistry)
            .where(FlowRegistry.name == name)
            .order_by(FlowRegistry.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_flow(self, spec: FlowSpec) -> FlowRegistry:
        """
        Crea un nuevo flujo a partir de una especificación FlowSpec.
        Serializa las configuraciones de disparadores y pasos a formato JSON.

        Args:
            spec: DTO con la especificación completa del flujo.

        Returns:
            La instancia de FlowRegistry persistida.
        """
        # Convert spec to DB model
        flow_data = spec.model_dump(exclude={"row_version", "id"})
        
        # Handle fields that need serialization if not handled by SQLModel/Pydantic bridge automatically
        # FlowRegistry definitions:
        # trigger_config: str = Field(default="{}", sa_column=Column(Text))
        # steps: str = Field(default="[]", sa_column=Column(Text))
        
        is_active_flag = spec.is_active if spec.status != "DRAFT" else False

        # Prepare data for insertion
        db_flow = FlowRegistry(
            name=spec.name,
            description=spec.description,
            version=spec.version or "0.1.0",
            status=spec.status or "DRAFT",
            row_version=0, # Start at 0
            owner_scope=spec.owner_scope,
            trigger_type=spec.trigger_type,
            trigger_config=json.dumps(spec.trigger_config),
            trigger_id=spec.trigger_id,
            steps=json.dumps([s.model_dump(mode='json') for s in spec.steps]),
            is_active=is_active_flag
        )
        
        self.session.add(db_flow)
        await self.session.commit()
        await self.session.refresh(db_flow)
        
        # Subscribe to trigger if active
        if db_flow.is_active and db_flow.trigger_id:
            # We need the trigger config to subscribe? 
            # Subscribing only needs ID usually but method signature asks for config object or at least we get it.
            # get_trigger might be needed.
            # Actually trigger_lifecycle_manager.subscribe takes (trigger: TriggerConfig, flow_id: int).
            # So we need to fetch the trigger.
            # But wait, trigger_lifecycle_manager.subscribe fetches trigger from DB? No, it takes object.
            # Let's check trigger_lifecycle_manager implementation.
            # It logs trigger.id and trigger.type.
            # So I should fetch the trigger first.
            async with AsyncSession(client_engine) as session:
                 trigger = await session.get(TriggerConfig, db_flow.trigger_id)
                 if trigger:
                     await trigger_lifecycle_manager.subscribe(trigger, db_flow.id)
                     
        return db_flow

    async def update_flow(self, flow_id: int, updates: FlowSpec) -> FlowRegistry:
        """
        Actualiza un flujo existente utilizando bloqueo optimista.
        Verifica que la versión enviada coincida con la de la base de datos para evitar colisiones.

        Args:
            flow_id: ID del flujo a actualizar.
            updates: Nueva especificación del flujo.

        Raises:
            NoResultFound: Si el flujo no existe.
            OptimisticLockError: Si hay un conflicto de versiones.

        Returns:
            La instancia de FlowRegistry actualizada.
        """
        db_flow = await self.get_flow(flow_id)
        if not db_flow:
            raise NoResultFound(f"Flow {flow_id} not found")

        # Optimistic Locking Check
        if db_flow.row_version != updates.row_version:
            raise OptimisticLockError(
                f"Conflict: Database version {db_flow.row_version} != Update version {updates.row_version}"
            )

        # Detect changes for subscription management
        was_active = db_flow.is_active
        old_trigger_id = db_flow.trigger_id
        
        # Apply updates
        db_flow.name = updates.name
        db_flow.description = updates.description
        db_flow.version = updates.version
        db_flow.status = updates.status
        db_flow.trigger_type = updates.trigger_type
        db_flow.trigger_config = json.dumps(updates.trigger_config)
        db_flow.steps = json.dumps([s.model_dump(mode='json') for s in updates.steps])
        db_flow.is_active = updates.is_active if updates.status != "DRAFT" else False
        db_flow.owner_scope = updates.owner_scope
        db_flow.trigger_id = updates.trigger_id
        
        # Increment row_version
        db_flow.row_version += 1
        
        self.session.add(db_flow)
        await self.session.commit()
        await self.session.refresh(db_flow)
        
        # Handle subscription changes
        # 1. Flow became inactive or trigger changed: Unsubscribe old
        if (was_active and not db_flow.is_active) or (was_active and old_trigger_id and old_trigger_id != db_flow.trigger_id):
            if old_trigger_id:
                await trigger_lifecycle_manager.unsubscribe(old_trigger_id, db_flow.id)
                
        # 2. Flow became active or trigger changed: Subscribe new
        if (db_flow.is_active and not was_active) or (db_flow.is_active and db_flow.trigger_id != old_trigger_id):
            if db_flow.trigger_id:
                async with AsyncSession(client_engine) as session:
                    trigger = await session.get(TriggerConfig, db_flow.trigger_id)
                    if trigger:
                        await trigger_lifecycle_manager.subscribe(trigger, db_flow.id)
                        
        return db_flow

    async def update_flow_metadata(self, flow_id: int, name: str, description: str) -> bool:
        """
        Actualiza los metadatos básicos de un flujo.
        """
        async with AsyncSession(client_engine) if not self.session else self.session as session:
            db_flow = await session.get(FlowRegistry, flow_id)
            if not db_flow:
                return False
            
            db_flow.name = name
            db_flow.description = description
            db_flow.updated_at = datetime.utcnow()
            session.add(db_flow)
            if not self.session:
                await session.commit()
            return True

    async def delete_flow(self, flow_id: int) -> bool:
        """
        Realiza un borrado lógico de un flujo marcándolo como DEPRECATED.

        Args:
            flow_id: ID del flujo a "eliminar".

        Returns:
            True si se marcó correctamente, False si el flujo no existe.
        """
        db_flow = await self.get_flow(flow_id)
        if not db_flow:
            return False
            
        db_flow.status = "DEPRECATED"
        self.session.add(db_flow)
        await self.session.commit()
        
        # Unsubscribe if valid trigger
        if db_flow.trigger_id:
             await trigger_lifecycle_manager.unsubscribe(db_flow.trigger_id, flow_id)
             
        return True

    async def create_etl_flow(self, execution_id: str, name: str, description: str = None) -> FlowRegistry:
        """
        Crea un nuevo flujo a partir de la ejecución de un Job ETL existente.
        Genera un paso de transformación IA basado en el script utilizado en el Job.

        Args:
            execution_id: ID de ejecución del Job ETL de origen.
            name: Nombre para el nuevo flujo.
            description: Descripción opcional.

        Returns:
            La instancia de FlowRegistry creada.
        """
        # 1. Fetch Job
        stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == execution_id)
        result = await self.session.execute(stmt)
        # Get the most recent one if multiple (retry history logic might create multiples with same execution_id? 
        # Actually standard practice is unique execution_id per run OR one job entry updated.
        # We'll take the latest just in case)
        job = result.scalars().first()
        
        if not job:
            raise NoResultFound(f"ETL Execution {execution_id} not found")
            
        # 2. Create FlowSpec
        etl_step = TaskSpec(
            type="etl_transform",
            name="AI Transformation",
            config={
                "script": job.script_content,
                "target_format": job.target_format,
                "execution_metadata": job.execution_metadata
            },
            retries=1
        )
        
        flow_spec = FlowSpec(
            name=name,
            description=description or f"Generated from ETL Job {execution_id}",
            version="1.0.0",
            status="PUBLISHED",
            steps=[etl_step],
            trigger_type="manual",
            is_active=True
        )
        
        # 3. Create Flow
        return await self.create_flow(flow_spec)

    async def create_flow_version(self, flow_id: int) -> FlowRegistry:
        """
        Crea una nueva versión del flujo como borrador.
        Incrementa la versión menor (ej: 0.1.0 -> 0.2.0).
        Mantiene el mismo nombre para que get_flow_history() pueda agrupar versiones.
        """
        original = await self.get_flow(flow_id)
        if not original:
            raise NoResultFound(f"Flow {flow_id} not found")

        # Incrementar versión (X.Y.Z -> X.Y+1.0)
        try:
            parts = original.version.split('.')
            if len(parts) >= 2:
                parts[1] = str(int(parts[1]) + 1)
                if len(parts) >= 3:
                    parts[2] = "0"
                new_version = '.'.join(parts)
            else:
                new_version = f"{original.version}.1.0"
        except:
            new_version = f"{original.version}.1"

        new_flow = FlowRegistry(
            name=original.name,  # Mismo nombre para agrupar versiones
            description=original.description or f"Versión {new_version}",
            version=new_version,
            status='DRAFT',
            row_version=0,  # Nueva versión empieza en 0
            steps=original.steps,  # Copiar estructura serializada
            trigger_type=original.trigger_type,
            trigger_config=original.trigger_config,
            owner_scope=original.owner_scope,
            is_active=False
        )

        self.session.add(new_flow)
        await self.session.commit()
        await self.session.refresh(new_flow)
        return new_flow

    def _to_spec(self, record: FlowRegistry) -> FlowSpec:
        """
        Helper para convertir un modelo de base de datos a un DTO FlowSpec.
        Des-serializa los campos JSON de disparadores y pasos.
        """
        from automatia_shared.dtos import TaskSpec
        return FlowSpec(
            name=record.name,
            description=record.description,
            version=record.version,
            status=record.status,
            row_version=record.row_version,
            owner_scope=record.owner_scope,
            trigger_type=record.trigger_type,
            trigger_config=json.loads(record.trigger_config),
            trigger_id=record.trigger_id,
            steps=[TaskSpec(**s) for s in json.loads(record.steps)],
            is_active=record.is_active,
        )

# Singleton Instance
flow_registry_service = FlowRegistryService()
