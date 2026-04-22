"""
Tests para el modelo AutomatismPackage - Almacena información de paquetes exportados/importados.
Prompt 1.1 del sistema de exportación/importación de automatismos.

TDD: Estos tests se escriben ANTES de implementar el modelo.
"""
import pytest
import uuid
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Importar los modelos ANTES del fixture para que se registren en SQLModel.metadata
from client_app.app.database.models import (
    AutomatismPackage,
    PackageType,
    PackageStatus
)


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


class TestAutomatismPackageModel:
    """Tests para el modelo AutomatismPackage."""

    @pytest.mark.asyncio
    async def test_create_package_record(self, db_session):
        """Crear registro con campos requeridos."""
        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Mi paquete de automatismos",
            description="Contiene scripts de extracción de facturas",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001-ABC",
            source_client_id="CLI-001-XYZ",
            source_partner_id="PARTNER-001",
            source_machine_id="MACHINE-001",
            signature_type="CLIENT",
            signer_id="CLI-001-XYZ",
            signature_value="abc123signature",
            signed_at=datetime.utcnow(),
            manifest_hash="sha256_manifest_hash_here",
            package_hash="sha256_package_hash_here",
            scripts_count=3,
            playbooks_count=0,
            workflows_count=0
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        assert package.id is not None
        assert package.name == "Mi paquete de automatismos"
        assert package.package_type == PackageType.SCRIPTS
        assert package.status == PackageStatus.CREATED  # default

    @pytest.mark.asyncio
    async def test_package_has_unique_id(self, db_session):
        """package_id es UUID único."""
        package_uuid = str(uuid.uuid4())

        package1 = AutomatismPackage(
            package_id=package_uuid,
            name="Paquete 1",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig1",
            signed_at=datetime.utcnow(),
            manifest_hash="hash1",
            package_hash="pkg_hash1"
        )

        db_session.add(package1)
        await db_session.commit()

        # Intentar crear otro con el mismo package_id debe fallar
        package2 = AutomatismPackage(
            package_id=package_uuid,  # mismo UUID
            name="Paquete 2",
            package_type=PackageType.PLAYBOOKS,
            source_license_id="LIC-002",
            source_client_id="CLI-002",
            source_partner_id="PARTNER-002",
            signature_type="CLIENT",
            signer_id="CLI-002",
            signature_value="sig2",
            signed_at=datetime.utcnow(),
            manifest_hash="hash2",
            package_hash="pkg_hash2"
        )

        db_session.add(package2)

        with pytest.raises(Exception):  # IntegrityError por unique constraint
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_package_tracks_source(self, db_session):
        """Registra license_id, client_id, partner_id de origen."""
        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete con origen",
            package_type=PackageType.MIXED,
            source_license_id="LIC-ORIGEN-123",
            source_client_id="CLI-ORIGEN-456",
            source_partner_id="PARTNER-ORIGEN-789",
            source_machine_id="MACHINE-ORIGEN-ABC",
            signature_type="CLIENT",
            signer_id="CLI-ORIGEN-456",
            signature_value="signature_value_here",
            signed_at=datetime.utcnow(),
            manifest_hash="manifest_hash_here",
            package_hash="package_hash_here"
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        # Verificar campos de origen
        assert package.source_license_id == "LIC-ORIGEN-123"
        assert package.source_client_id == "CLI-ORIGEN-456"
        assert package.source_partner_id == "PARTNER-ORIGEN-789"
        assert package.source_machine_id == "MACHINE-ORIGEN-ABC"

    @pytest.mark.asyncio
    async def test_package_tracks_signature(self, db_session):
        """Almacena tipo de firma (CLIENT/PARTNER) y valor."""
        signed_time = datetime.utcnow()

        # Paquete firmado por cliente
        package_client = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete firmado por cliente",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="hmac_sha256_client_signature",
            signed_at=signed_time,
            manifest_hash="hash1",
            package_hash="pkg_hash1"
        )

        # Paquete firmado por partner
        package_partner = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete firmado por partner",
            package_type=PackageType.WORKFLOW,
            source_license_id="LIC-002",
            source_client_id="CLI-002",
            source_partner_id="PARTNER-001",
            signature_type="PARTNER",
            signer_id="PARTNER-001",
            signature_value="rsa_partner_signature_base64",
            signed_at=signed_time,
            manifest_hash="hash2",
            package_hash="pkg_hash2"
        )

        db_session.add_all([package_client, package_partner])
        await db_session.commit()
        await db_session.refresh(package_client)
        await db_session.refresh(package_partner)

        # Verificar firma de cliente
        assert package_client.signature_type == "CLIENT"
        assert package_client.signer_id == "CLI-001"
        assert package_client.signature_value == "hmac_sha256_client_signature"
        assert package_client.signed_at == signed_time

        # Verificar firma de partner
        assert package_partner.signature_type == "PARTNER"
        assert package_partner.signer_id == "PARTNER-001"
        assert package_partner.signature_value == "rsa_partner_signature_base64"

    @pytest.mark.asyncio
    async def test_package_supports_workflow_type(self, db_session):
        """Soporta tipos SCRIPTS, PLAYBOOKS, WORKFLOW, MIXED."""
        packages = []

        for pkg_type in PackageType:
            package = AutomatismPackage(
                package_id=str(uuid.uuid4()),
                name=f"Paquete tipo {pkg_type.value}",
                package_type=pkg_type,
                source_license_id="LIC-001",
                source_client_id="CLI-001",
                source_partner_id="PARTNER-001",
                signature_type="CLIENT",
                signer_id="CLI-001",
                signature_value=f"sig_{pkg_type.value}",
                signed_at=datetime.utcnow(),
                manifest_hash=f"hash_{pkg_type.value}",
                package_hash=f"pkg_hash_{pkg_type.value}"
            )
            packages.append(package)
            db_session.add(package)

        await db_session.commit()

        # Verificar que se pueden filtrar por tipo
        for pkg_type in PackageType:
            stmt = select(AutomatismPackage).where(
                AutomatismPackage.package_type == pkg_type
            )
            result = await db_session.execute(stmt)
            found = result.scalars().all()
            assert len(found) == 1
            assert found[0].package_type == pkg_type

        # Verificar los valores del enum
        assert PackageType.SCRIPTS.value == "scripts"
        assert PackageType.PLAYBOOKS.value == "playbooks"
        assert PackageType.WORKFLOW.value == "workflow"
        assert PackageType.MIXED.value == "mixed"

    @pytest.mark.asyncio
    async def test_package_status_transitions(self, db_session):
        """Estados válidos (CREATED -> EXPORTED -> IMPORTED)."""
        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete con transiciones de estado",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig",
            signed_at=datetime.utcnow(),
            manifest_hash="hash",
            package_hash="pkg_hash"
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        # Estado inicial es CREATED
        assert package.status == PackageStatus.CREATED

        # Transición a EXPORTED
        package.status = PackageStatus.EXPORTED
        package.exported_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(package)

        assert package.status == PackageStatus.EXPORTED
        assert package.exported_at is not None

        # Transición a IMPORTED (en otro cliente)
        package.status = PackageStatus.IMPORTED
        package.imported_at = datetime.utcnow()
        package.imported_by_license_id = "LIC-DESTINO-002"
        await db_session.commit()
        await db_session.refresh(package)

        assert package.status == PackageStatus.IMPORTED
        assert package.imported_at is not None
        assert package.imported_by_license_id == "LIC-DESTINO-002"

        # Verificar los valores del enum de estado
        assert PackageStatus.CREATED.value == "created"
        assert PackageStatus.EXPORTED.value == "exported"
        assert PackageStatus.IMPORTED.value == "imported"
        assert PackageStatus.REJECTED.value == "rejected"

    @pytest.mark.asyncio
    async def test_package_content_counts(self, db_session):
        """El paquete registra conteo de scripts, playbooks y workflows."""
        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete mixto",
            package_type=PackageType.MIXED,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig",
            signed_at=datetime.utcnow(),
            manifest_hash="hash",
            package_hash="pkg_hash",
            scripts_count=5,
            playbooks_count=3,
            workflows_count=2
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        assert package.scripts_count == 5
        assert package.playbooks_count == 3
        assert package.workflows_count == 2

    @pytest.mark.asyncio
    async def test_package_dependencies_json(self, db_session):
        """Para tipo WORKFLOW, almacena dependencias en JSON."""
        import json

        dependencies = {
            "scripts": ["script_1", "script_2", "script_3"],
            "playbooks": ["playbook_1"]
        }

        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Workflow con dependencias",
            package_type=PackageType.WORKFLOW,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig",
            signed_at=datetime.utcnow(),
            manifest_hash="hash",
            package_hash="pkg_hash",
            scripts_count=3,
            playbooks_count=1,
            workflows_count=1,
            dependencies_json=json.dumps(dependencies)
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        # Verificar que se puede parsear el JSON de dependencias
        parsed_deps = json.loads(package.dependencies_json)
        assert parsed_deps["scripts"] == ["script_1", "script_2", "script_3"]
        assert parsed_deps["playbooks"] == ["playbook_1"]

    @pytest.mark.asyncio
    async def test_package_audit_timestamps(self, db_session):
        """Verificar timestamps de auditoría."""
        before_create = datetime.utcnow()

        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete con timestamps",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig",
            signed_at=datetime.utcnow(),
            manifest_hash="hash",
            package_hash="pkg_hash"
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        after_create = datetime.utcnow()

        # created_at debe estar entre before y after
        assert package.created_at is not None
        assert before_create <= package.created_at <= after_create

        # exported_at e imported_at deben ser None inicialmente
        assert package.exported_at is None
        assert package.imported_at is None
        assert package.imported_by_license_id is None

    @pytest.mark.asyncio
    async def test_package_hashes(self, db_session):
        """El paquete almacena hashes de manifiesto y ZIP."""
        manifest_hash = "a" * 64  # SHA256 tiene 64 caracteres hex
        package_hash = "b" * 64

        package = AutomatismPackage(
            package_id=str(uuid.uuid4()),
            name="Paquete con hashes",
            package_type=PackageType.SCRIPTS,
            source_license_id="LIC-001",
            source_client_id="CLI-001",
            source_partner_id="PARTNER-001",
            signature_type="CLIENT",
            signer_id="CLI-001",
            signature_value="sig",
            signed_at=datetime.utcnow(),
            manifest_hash=manifest_hash,
            package_hash=package_hash
        )

        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)

        assert package.manifest_hash == manifest_hash
        assert package.package_hash == package_hash
        assert len(package.manifest_hash) == 64
        assert len(package.package_hash) == 64
