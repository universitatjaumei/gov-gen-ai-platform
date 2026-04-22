"""
Tests para la relación Flujo-Átomo (FlowStep).
Prompt 1.2 del plan de refactorización del editor de flujos.

TDD: Estos tests se escriben ANTES de implementar el modelo.
"""
import pytest
import json
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from automatia_shared.enums import StepType
# Importar los modelos ANTES del fixture para que se registren en SQLModel.metadata
from client_app.app.database.models import AtomRegistry, FlowRegistry, FlowStep


@pytest.fixture
async def async_engine():
    """Crea un engine async en memoria para tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Fixture para crear sesión async."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def sample_flow(db_session) -> FlowRegistry:
    """Crea un flujo de ejemplo para los tests."""
    flow = FlowRegistry(
        name="Flujo de Procesamiento de Facturas",
        description="Procesa facturas PDF y envía notificaciones",
        version="1.0.0",
        status="DRAFT",
        trigger_type="folder_watcher"
    )
    db_session.add(flow)
    await db_session.commit()
    await db_session.refresh(flow)
    return flow


@pytest.fixture
async def sample_atoms(db_session) -> list[AtomRegistry]:
    """Crea átomos de ejemplo para los tests."""
    atoms = [
        AtomRegistry(
            name="Extracción PDF",
            atom_type=StepType.EXTRACTION,
            config_schema=json.dumps({
                "type": "object",
                "properties": {"config_id": {"type": "integer"}},
                "required": ["config_id"]
            }),
            default_config=json.dumps({"config_id": None})
        ),
        AtomRegistry(
            name="Llamada API REST",
            atom_type=StepType.API_FETCH,
            config_schema=json.dumps({
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "method": {"type": "string"}
                },
                "required": ["url"]
            }),
            default_config=json.dumps({"url": "", "method": "GET"})
        ),
        AtomRegistry(
            name="Enviar Email",
            atom_type=StepType.EMAIL_SEND,
            config_schema=json.dumps({
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"}
                },
                "required": ["to", "subject"]
            }),
            default_config=json.dumps({"to": "", "subject": ""})
        ),
    ]
    for atom in atoms:
        db_session.add(atom)
    await db_session.commit()
    for atom in atoms:
        await db_session.refresh(atom)
    return atoms


class TestFlowAtomRelation:
    """Tests para el modelo FlowStep y la relación Flujo-Átomo."""

    @pytest.mark.asyncio
    async def test_flow_can_have_multiple_atoms(self, db_session, sample_flow, sample_atoms):
        """Un flujo tiene varios átomos ordenados."""
        # Crear pasos que relacionan el flujo con los átomos
        steps = []
        for idx, atom in enumerate(sample_atoms):
            step = FlowStep(
                flow_id=sample_flow.id,
                atom_id=atom.id,
                step_order=idx,
                custom_name=f"Paso {idx + 1}",
                output_var_name=f"resultado_paso_{idx + 1}"
            )
            db_session.add(step)
            steps.append(step)

        await db_session.commit()

        # Verificar que el flujo tiene 3 pasos
        stmt = select(FlowStep).where(
            FlowStep.flow_id == sample_flow.id
        ).order_by(FlowStep.step_order)
        result = await db_session.execute(stmt)
        flow_steps = result.scalars().all()

        assert len(flow_steps) == 3
        assert flow_steps[0].step_order == 0
        assert flow_steps[1].step_order == 1
        assert flow_steps[2].step_order == 2

    @pytest.mark.asyncio
    async def test_atom_can_belong_to_multiple_flows(self, db_session, sample_atoms):
        """El mismo átomo puede usarse en varios flujos."""
        # Crear dos flujos diferentes
        flow1 = FlowRegistry(
            name="Flujo de Ventas",
            trigger_type="manual"
        )
        flow2 = FlowRegistry(
            name="Flujo de Compras",
            trigger_type="email"
        )
        db_session.add_all([flow1, flow2])
        await db_session.commit()
        await db_session.refresh(flow1)
        await db_session.refresh(flow2)

        # Usar el mismo átomo (Extracción PDF) en ambos flujos
        extraction_atom = sample_atoms[0]

        step_flow1 = FlowStep(
            flow_id=flow1.id,
            atom_id=extraction_atom.id,
            step_order=0,
            custom_name="Extraer datos venta"
        )
        step_flow2 = FlowStep(
            flow_id=flow2.id,
            atom_id=extraction_atom.id,
            step_order=0,
            custom_name="Extraer datos compra"
        )

        db_session.add_all([step_flow1, step_flow2])
        await db_session.commit()

        # Verificar que el átomo está en ambos flujos
        stmt = select(FlowStep).where(FlowStep.atom_id == extraction_atom.id)
        result = await db_session.execute(stmt)
        uses = result.scalars().all()

        assert len(uses) == 2
        flow_ids = {step.flow_id for step in uses}
        assert flow_ids == {flow1.id, flow2.id}

    @pytest.mark.asyncio
    async def test_flow_step_has_order(self, db_session, sample_flow, sample_atoms):
        """Los pasos tienen un orden (step_order) que determina la secuencia."""
        # Crear pasos en orden inverso para verificar que el orden se respeta
        step3 = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[2].id,
            step_order=2
        )
        step1 = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[0].id,
            step_order=0
        )
        step2 = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[1].id,
            step_order=1
        )

        # Añadir en orden desordenado
        db_session.add_all([step3, step1, step2])
        await db_session.commit()

        # Recuperar ordenados por step_order
        stmt = select(FlowStep).where(
            FlowStep.flow_id == sample_flow.id
        ).order_by(FlowStep.step_order)
        result = await db_session.execute(stmt)
        ordered_steps = result.scalars().all()

        # Verificar orden correcto
        assert ordered_steps[0].atom_id == sample_atoms[0].id
        assert ordered_steps[1].atom_id == sample_atoms[1].id
        assert ordered_steps[2].atom_id == sample_atoms[2].id

    @pytest.mark.asyncio
    async def test_flow_step_has_custom_config(self, db_session, sample_flow, sample_atoms):
        """Cada uso puede sobrescribir configuración del átomo base."""
        api_atom = sample_atoms[1]  # Llamada API REST

        # Crear un paso con configuración personalizada
        custom_config = {
            "url": "https://api.ejemplo.com/facturas",
            "method": "POST",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 60
        }

        step = FlowStep(
            flow_id=sample_flow.id,
            atom_id=api_atom.id,
            step_order=0,
            custom_name="Enviar factura a ERP",
            custom_config=json.dumps(custom_config),
            output_var_name="respuesta_erp"
        )

        db_session.add(step)
        await db_session.commit()
        await db_session.refresh(step)

        # Verificar que la configuración personalizada se guardó
        assert step.custom_config is not None
        parsed_config = json.loads(step.custom_config)
        assert parsed_config["url"] == "https://api.ejemplo.com/facturas"
        assert parsed_config["method"] == "POST"
        assert parsed_config["timeout"] == 60

        # Verificar que el átomo original no se modificó
        await db_session.refresh(api_atom)
        atom_default = json.loads(api_atom.default_config)
        assert atom_default["method"] == "GET"  # Sigue siendo GET

    @pytest.mark.asyncio
    async def test_delete_atom_preserves_flow_steps(self, db_session, sample_flow, sample_atoms):
        """Al eliminar átomo (soft delete), los pasos existentes se mantienen con referencia nullable."""
        extraction_atom = sample_atoms[0]

        # Crear un paso usando el átomo
        step = FlowStep(
            flow_id=sample_flow.id,
            atom_id=extraction_atom.id,
            step_order=0,
            custom_name="Extracción legacy"
        )
        db_session.add(step)
        await db_session.commit()
        await db_session.refresh(step)
        step_id = step.id

        # "Eliminar" el átomo (soft delete)
        extraction_atom.is_active = False
        await db_session.commit()

        # El paso sigue existiendo con su referencia al átomo
        stmt = select(FlowStep).where(FlowStep.id == step_id)
        result = await db_session.execute(stmt)
        preserved_step = result.scalar_one()

        assert preserved_step is not None
        assert preserved_step.atom_id == extraction_atom.id
        assert preserved_step.custom_name == "Extracción legacy"

    @pytest.mark.asyncio
    async def test_flow_step_without_atom_legacy(self, db_session, sample_flow):
        """Pasos legacy pueden existir sin referencia a átomo (atom_id=None)."""
        # Paso legacy sin átomo asociado
        legacy_step = FlowStep(
            flow_id=sample_flow.id,
            atom_id=None,  # Sin átomo - paso legacy
            step_order=0,
            custom_name="Paso legacy manual",
            custom_config=json.dumps({
                "type": "extraction",
                "config_id": 5
            }),
            output_var_name="datos_legacy"
        )

        db_session.add(legacy_step)
        await db_session.commit()
        await db_session.refresh(legacy_step)

        assert legacy_step.id is not None
        assert legacy_step.atom_id is None
        assert legacy_step.custom_name == "Paso legacy manual"

    @pytest.mark.asyncio
    async def test_flow_step_output_var_name(self, db_session, sample_flow, sample_atoms):
        """El nombre de variable de salida permite conectar pasos entre sí."""
        # Paso 1: Extracción
        step1 = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[0].id,
            step_order=0,
            output_var_name="datos_factura"
        )

        # Paso 2: API que usa la salida del paso 1
        step2 = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[1].id,
            step_order=1,
            custom_config=json.dumps({
                "url": "https://api.erp.com/upload",
                "body": "{{datos_factura}}"  # Referencia a la salida del paso 1
            }),
            output_var_name="respuesta_api"
        )

        db_session.add_all([step1, step2])
        await db_session.commit()

        # Verificar que los nombres de variable son únicos y correctos
        stmt = select(FlowStep).where(
            FlowStep.flow_id == sample_flow.id
        ).order_by(FlowStep.step_order)
        result = await db_session.execute(stmt)
        steps = result.scalars().all()

        assert steps[0].output_var_name == "datos_factura"
        assert steps[1].output_var_name == "respuesta_api"

        # La configuración del paso 2 referencia la variable del paso 1
        step2_config = json.loads(steps[1].custom_config)
        assert "{{datos_factura}}" in step2_config["body"]

    @pytest.mark.asyncio
    async def test_flow_step_created_at_timestamp(self, db_session, sample_flow, sample_atoms):
        """El campo created_at se establece automáticamente."""
        before_create = datetime.utcnow()

        step = FlowStep(
            flow_id=sample_flow.id,
            atom_id=sample_atoms[0].id,
            step_order=0
        )

        db_session.add(step)
        await db_session.commit()
        await db_session.refresh(step)

        after_create = datetime.utcnow()

        assert step.created_at is not None
        assert before_create <= step.created_at <= after_create
