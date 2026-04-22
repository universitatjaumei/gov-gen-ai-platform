"""
Client database configuration and initialization.

This module manages the local client database (client_local.db) which stores:
- User playbooks and extraction configs
- API credentials
- Extraction logs
- Workflow configurations
"""

import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Import models to register them with SQLModel metadata
from client_app.app.database import models

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

CLIENT_DB_URL = "sqlite+aiosqlite:///data/client_local.db"

sqlite_connect_args = {
    "check_same_thread": False,
    "timeout": 15
}

client_engine = create_async_engine(
    CLIENT_DB_URL,
    echo=False,
    future=True,
    connect_args=sqlite_connect_args
)


def get_db():
    """
    Returns an async database session.
    Usage: async with get_db() as session:
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    return AsyncSession(client_engine)

db_session = get_db
get_session = get_db


async def init_client_db():
    """Initialize client database and create all tables."""
    async with client_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))

    # Run migrations for existing tables
    await run_migrations()


async def run_migrations():
    """Run schema migrations for columns added after initial release."""
    async with client_engine.begin() as conn:
        # Migration: Add origin tracking columns to customscript table
        await _migrate_customscript_origin_columns(conn)
        # Migration: Add origin tracking columns to rpaplaybook table
        await _migrate_rpaplaybook_origin_columns(conn)
        # Migration: Add cleanup columns
        await _migrate_cleanup_columns(conn)
        # Migration: Add server connection partner public key
        await _migrate_serverconnection_public_key(conn)
        # Migration: Add RunManifestLog table if missing
        await _create_run_manifest_table_if_missing(conn)
        # Migration: Update ReportTemplate columns (is_system, structure, etc.)
        await _migrate_report_template_columns(conn)
        # Migration: Update AtomRegistry columns (subtype, contracts)
        await _migrate_atom_registry_columns(conn)
        # Migration: Add status column to AtomRegistry
        await _migrate_atom_status_column(conn)
        # Migration: Add body column to APIEndpointConfig
        await _migrate_api_endpoint_body_column(conn)
        # Migration: Add watch_mode column to WebWatcherConfig
        await _migrate_web_watcher_watch_mode_column(conn)
        # Migration: Add name column to WebWatcherConfig
        await _migrate_web_watcher_name_column(conn)
        # Migration: Add trigger_id to FlowRegistry
        await _migrate_flow_registry_trigger_columns(conn)
        # Migration: Add transformation_mode to ETLJobHistory
        await _migrate_etl_job_history_columns(conn)
        # Migration: Add diff-related columns to WebWatcher tables
        await _migrate_web_watcher_diff_columns(conn)
        # Migration: Add sample_data column to AtomRegistry (data preview feature)
        await _migrate_atom_registry_sample_data(conn)
        # Migration: Create EnterpriseAuditLog table for PII tracking
        await _create_enterprise_audit_log_table(conn)
        # Migration: Add status column to UserExtractionConfig
        await _migrate_userextractionconfig_status_column(conn)


async def seed_client_db():
    """
    Populates client DB with default configurations if needed.
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select
    from client_app.app.database.models import ServerConnection, ReportTemplate

    print("[CLIENT DB] Checking Default Configuration...")

    async with AsyncSession(client_engine) as session:
        # Check if ServerConnection exists
        result = await session.exec(select(ServerConnection))
        existing_conn = result.first()

        if not existing_conn:
            print("[CLIENT DB] Seeding Default Server Connection (DemoCorp)")
            # Default connection to local server with Demo Key
            default_conn = ServerConnection(
                brain_url="http://localhost:8080", # Default Dev URL
                license_key="demo_key_123",        # Raw key matching server hash
                is_active=True
            )
            session.add(default_conn)
            await session.commit()
            print("[CLIENT DB] Server Connection Seeded.")
        else:
            # Optional: Update if needed?
            pass

    # Seed cleanup policies
    from client_app.app.services.cleanup_service import cleanup_service
    await cleanup_service.seed_default_policies()

    # Seed report templates
    await seed_report_templates()

    print("[CLIENT DB] Initialization complete.")


async def seed_report_templates():
    """
    Crea las plantillas de reporte del sistema si no existen.
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select
    from client_app.app.database.models import ReportTemplate
    import json

    async with AsyncSession(client_engine) as session:
        # Verificar si ya existen plantillas del sistema
        result = await session.exec(
            select(ReportTemplate).where(ReportTemplate.is_system == True)
        )
        existing = result.all()

        if existing:
            print(f"[CLIENT DB] Report templates already exist ({len(existing)} found)")
            return

        print("[CLIENT DB] Seeding default report templates...")

        # Plantilla 1: Informe Generico
        generic_template = ReportTemplate(
            name="Informe Generico",
            description="Plantilla base para informes con titulo, resumen, secciones y tabla de datos.",
            format="pdf",
            template_type="builtin",
            template_source="generic_report.html",
            available_sections=json.dumps(["title", "subtitle", "date", "summary", "sections", "table"]),
            default_styles=json.dumps({
                "title_color": "#1a365d",
                "title_size": 24,
                "body_size": 12
            }),
            is_system=True,
            is_active=True
        )
        session.add(generic_template)

        # Plantilla 2: Informe Base (mas completo)
        base_template = ReportTemplate(
            name="Informe Profesional",
            description="Plantilla profesional con logo, tabla de contenidos, multiples secciones y graficos.",
            format="pdf",
            template_type="builtin",
            template_source="base_report.html",
            available_sections=json.dumps(["logo", "title", "subtitle", "date", "summary", "sections", "table", "charts"]),
            default_styles=json.dumps({
                "title_color": "#2c5282",
                "title_size": 28,
                "body_size": 11,
                "table_header_bg": "#4a5568"
            }),
            is_system=True,
            is_active=True
        )
        session.add(base_template)

        # Plantilla 3: Reporte de Datos (solo tabla)
        data_template = ReportTemplate(
            name="Reporte de Datos",
            description="Plantilla minimalista enfocada en la tabla de datos. Ideal para exportar resultados de extraccion.",
            format="pdf",
            template_type="reportlab",
            template_source=None,
            available_sections=json.dumps(["title", "date", "table"]),
            default_styles=json.dumps({
                "title_size": 18,
                "body_size": 10
            }),
            is_system=True,
            is_active=True
        )
        session.add(data_template)

        await session.commit()
        print("[CLIENT DB] 3 default report templates seeded.")


async def _migrate_customscript_origin_columns(conn):
    """
    Migration: Add origin tracking columns to customscript table.
    These columns were added to support import/export of automatisms.
    """
    # Check which columns exist
    result = await conn.execute(text("PRAGMA table_info(customscript)"))
    existing_columns = {row[1] for row in result.fetchall()}

    columns_to_add = [
        ("origin_license_id", "TEXT"),
        ("origin_package_id", "TEXT"),
        ("original_status", "TEXT"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"[MIGRATION] Adding column {col_name} to customscript table")
            await conn.execute(text(f"ALTER TABLE customscript ADD COLUMN {col_name} {col_type}"))


async def _migrate_rpaplaybook_origin_columns(conn):
    """
    Migration: Add origin tracking columns to rpaplaybook table.
    These columns were added to support import/export of automatisms.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rpaplaybook'"
    ))
    if not result.fetchone():
        return  # Table doesn't exist yet, will be created with all columns

    # Check which columns exist
    result = await conn.execute(text("PRAGMA table_info(rpaplaybook)"))
    existing_columns = {row[1] for row in result.fetchall()}

    columns_to_add = [
        ("content_hash", "TEXT"),
        ("origin_license_id", "TEXT"),
        ("origin_package_id", "TEXT"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"[MIGRATION] Adding column {col_name} to rpaplaybook table")
            await conn.execute(text(f"ALTER TABLE rpaplaybook ADD COLUMN {col_name} {col_type}"))


async def _migrate_cleanup_columns(conn):
    """
    Migration: Add new columns to cleanup related tables.
    """
    # 1. CleanupSchedulerConfig
    result = await conn.execute(text("PRAGMA table_info(cleanupschedulerconfig)"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    if "interval_hours" not in existing_columns:
        print("[MIGRATION] Adding column interval_hours to cleanupschedulerconfig")
        await conn.execute(text("ALTER TABLE cleanupschedulerconfig ADD COLUMN interval_hours INTEGER DEFAULT 24"))

    # 2. CleanupLog
    result = await conn.execute(text("PRAGMA table_info(cleanuplog)"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    if "message" not in existing_columns:
        print("[MIGRATION] Adding column message to cleanuplog")
        await conn.execute(text("ALTER TABLE cleanuplog ADD COLUMN message TEXT"))


async def _migrate_serverconnection_public_key(conn):
    """
    Migration: Add partner_public_key column to serverconnection table.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='serverconnection'"
    ))
    if not result.fetchone():
        return

    # Check if column exists
    result = await conn.execute(text("PRAGMA table_info(serverconnection)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "partner_public_key" not in existing_columns:
        print("[MIGRATION] Adding column partner_public_key to serverconnection")
        await conn.execute(text("ALTER TABLE serverconnection ADD COLUMN partner_public_key TEXT"))

async def _create_run_manifest_table_if_missing(conn):
    """
    Ensure RunManifestLog table exists.
    Useful when updating existing databases without full recreate.
    """
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='runmanifestlog'"
    ))
    if not result.fetchone():
        print("[MIGRATION] Creating RunManifestLog table manually for existing DB")
        # SQL definition matching RunManifestLog model
        await conn.execute(text("""
            CREATE TABLE runmanifestlog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id VARCHAR NOT NULL,
                client_id VARCHAR,
                service_id VARCHAR NOT NULL,
                model_used VARCHAR NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                status VARCHAR NOT NULL DEFAULT 'success',
                error_message TEXT,
                is_synced BOOLEAN NOT NULL DEFAULT 0,
                synced_at DATETIME,
                created_at DATETIME NOT NULL
            );
        """))
        await conn.execute(text("CREATE INDEX ix_runmanifestlog_is_synced ON runmanifestlog (is_synced)"))
        print("[MIGRATION] RunManifestLog table created.")


async def _migrate_report_template_columns(conn):
    """
    Migration: Add new columns to report_templates table (Prompt 1 features).
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='report_templates'"
    ))
    if not result.fetchone():
        return

    # Check existing columns
    result = await conn.execute(text("PRAGMA table_info(report_templates)"))
    existing_columns = {row[1] for row in result.fetchall()}

    # Columns to add
    columns_to_add = [
        ("is_system", "BOOLEAN DEFAULT 0"),
        ("structure", "JSON DEFAULT '{}'"),
        ("input_schema", "JSON DEFAULT '{}'"),
        ("style_config", "JSON DEFAULT '{}'"),
        ("preview_data", "JSON DEFAULT '{}'"),
        ("category", "VARCHAR DEFAULT 'general'"),
        ("tags", "JSON DEFAULT '[]'"),
        ("version", "VARCHAR DEFAULT '1.0'")
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"[MIGRATION] Adding column {col_name} to report_templates")
            await conn.execute(text(f"ALTER TABLE report_templates ADD COLUMN {col_name} {col_type}"))


async def _migrate_atom_registry_columns(conn):
    """
    Migration: Add missing columns to atom_registry (subtype, contracts).
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='atom_registry'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(atom_registry)"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    # Define columns to verify
    columns_to_add = [
        ("subtype", "TEXT"),
        ("input_contract", "TEXT"),
        ("output_contract", "TEXT"),
        ("dependencies", "TEXT"), # JSON stored as TEXT in sqlite often
        ("has_stepper", "BOOLEAN DEFAULT 1"),
        ("has_variables", "BOOLEAN DEFAULT 1"),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"[MIGRATION] Adding column {col_name} to atom_registry")
            await conn.execute(text(f"ALTER TABLE atom_registry ADD COLUMN {col_name} {col_type}"))


async def _migrate_atom_status_column(conn):
    """
    Migration: Add status column to atom_registry and migrate based on is_active.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='atom_registry'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(atom_registry)"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    if "status" not in existing_columns:
        print("[MIGRATION] Adding column status to atom_registry")
        # Add column with default DRAFT
        await conn.execute(text("ALTER TABLE atom_registry ADD COLUMN status TEXT DEFAULT 'DRAFT'"))

        # Migrate existing data: is_active=True -> status='PUBLISHED'
        print("[MIGRATION] Migrating existing atoms status based on is_active")
        await conn.execute(text("UPDATE atom_registry SET status = 'PUBLISHED' WHERE is_active = 1"))


async def _migrate_api_endpoint_body_column(conn):
    """
    Migration: Add body column to apiendpointconfig table.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='apiendpointconfig'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(apiendpointconfig)"))
    existing_columns = {row[1] for row in result.fetchall()}
    
    if "body" not in existing_columns:
        print("[MIGRATION] Adding column body to apiendpointconfig")
        await conn.execute(text("ALTER TABLE apiendpointconfig ADD COLUMN body TEXT DEFAULT '{}'"))


async def _migrate_web_watcher_watch_mode_column(conn):
    """
    Migration: Add watch_mode column to webwatcherconfig table.
    This column enables full-page monitoring mode vs specific selector mode.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='webwatcherconfig'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(webwatcherconfig)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "watch_mode" not in existing_columns:
        print("[MIGRATION] Adding column watch_mode to webwatcherconfig")
        await conn.execute(text("ALTER TABLE webwatcherconfig ADD COLUMN watch_mode TEXT DEFAULT 'selector'"))


async def _migrate_web_watcher_name_column(conn):
    """
    Migration: Add name column to webwatcherconfig table.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='webwatcherconfig'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(webwatcherconfig)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "name" not in existing_columns:
        print("[MIGRATION] Adding column name to webwatcherconfig")
        await conn.execute(text("ALTER TABLE webwatcherconfig ADD COLUMN name TEXT DEFAULT ''"))


async def _migrate_flow_registry_trigger_columns(conn):
    """
    Migration: Add trigger_id column to flowregistry table.
    """
    # Check which columns exist
    result = await conn.execute(text("PRAGMA table_info(flowregistry)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "trigger_id" not in existing_columns:
        print("[MIGRATION] Adding column trigger_id to flowregistry")
        await conn.execute(text("ALTER TABLE flowregistry ADD COLUMN trigger_id INTEGER"))
        await conn.execute(text("CREATE INDEX ix_flowregistry_trigger_id ON flowregistry (trigger_id)"))


async def _migrate_etl_job_history_columns(conn):
    """
    Migration: Add transformation_mode column to etljobhistory table.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='etljobhistory'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(etljobhistory)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "transformation_mode" not in existing_columns:
        print("[MIGRATION] Adding column transformation_mode to etljobhistory")
        await conn.execute(text("ALTER TABLE etljobhistory ADD COLUMN transformation_mode TEXT DEFAULT 'ai'"))


async def _migrate_web_watcher_diff_columns(conn):
    """
    Migration: Add diff-related columns to WebWatcherConfig and WebWatcherHistory.
    Enables detailed content capture and diff visualization.
    """
    # --- WebWatcherConfig ---
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='webwatcherconfig'"
    ))
    if result.fetchone():
        result = await conn.execute(text("PRAGMA table_info(webwatcherconfig)"))
        existing_columns = {row[1] for row in result.fetchall()}

        columns_to_add = [
            ("last_content_text", "TEXT"),
            ("last_content_html", "TEXT"),
            ("capture_detailed_content", "BOOLEAN DEFAULT 0"),
        ]

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"[MIGRATION] Adding column {col_name} to webwatcherconfig")
                await conn.execute(text(f"ALTER TABLE webwatcherconfig ADD COLUMN {col_name} {col_type}"))

    # --- WebWatcherHistory ---
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='webwatcherhistory'"
    ))
    if result.fetchone():
        result = await conn.execute(text("PRAGMA table_info(webwatcherhistory)"))
        existing_columns = {row[1] for row in result.fetchall()}

        columns_to_add = [
            ("diff_text", "TEXT"),
            ("diff_html", "TEXT"),
        ]

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"[MIGRATION] Adding column {col_name} to webwatcherhistory")
                await conn.execute(text(f"ALTER TABLE webwatcherhistory ADD COLUMN {col_name} {col_type}"))


async def _migrate_atom_registry_sample_data(conn):
    """
    Migration: Add sample_data column to atom_registry.
    Supports the data preview feature for flow design (PLAN_DATA_PREVIEW_FLOWS).
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='atom_registry'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(atom_registry)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "sample_data" not in existing_columns:
        print("[MIGRATION] Adding column sample_data to atom_registry")
        await conn.execute(text("ALTER TABLE atom_registry ADD COLUMN sample_data TEXT"))


async def _create_enterprise_audit_log_table(conn):
    """
    Migration: Create enterprise_audit_log table for PII operation tracking.
    This table stores immutable audit records for RGPD compliance.
    """
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='enterprise_audit_log'"
    ))
    if not result.fetchone():
        print("[MIGRATION] Creating enterprise_audit_log table")
        await conn.execute(text("""
            CREATE TABLE enterprise_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                user_id VARCHAR,
                action_type VARCHAR NOT NULL,
                module VARCHAR NOT NULL,
                task_log_id INTEGER,
                execution_id VARCHAR,
                pii_detected_count INTEGER NOT NULL DEFAULT 0,
                pii_protected_count INTEGER NOT NULL DEFAULT 0,
                pii_types JSON DEFAULT '{}',
                anonymization_method VARCHAR,
                source_description VARCHAR,
                target_description VARCHAR,
                ip_address VARCHAR,
                additional_context JSON DEFAULT '{}',
                risk_level VARCHAR NOT NULL DEFAULT 'low',
                security_flags JSON DEFAULT '{}',
                created_at DATETIME NOT NULL,
                FOREIGN KEY (task_log_id) REFERENCES tasklog(id)
            );
        """))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_timestamp ON enterprise_audit_log (timestamp)"))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_user_id ON enterprise_audit_log (user_id)"))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_action_type ON enterprise_audit_log (action_type)"))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_module ON enterprise_audit_log (module)"))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_execution_id ON enterprise_audit_log (execution_id)"))
        await conn.execute(text("CREATE INDEX ix_enterprise_audit_log_risk_level ON enterprise_audit_log (risk_level)"))
        print("[MIGRATION] enterprise_audit_log table created with indexes")


async def _migrate_userextractionconfig_status_column(conn):
    """
    Migration: Add status column to userextractionconfig table.
    """
    # Check if table exists
    result = await conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='userextractionconfig'"
    ))
    if not result.fetchone():
        return

    # Check columns
    result = await conn.execute(text("PRAGMA table_info(userextractionconfig)"))
    existing_columns = {row[1] for row in result.fetchall()}

    if "status" not in existing_columns:
        print("[MIGRATION] Adding column status to userextractionconfig")
        await conn.execute(text("ALTER TABLE userextractionconfig ADD COLUMN status TEXT DEFAULT 'published'"))
