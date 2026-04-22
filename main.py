import sys
from typing import Optional
from pathlib import Path

# Add shared library to path
_project_root = Path(__file__).parent
sys.path.insert(0, str(_project_root / 'shared'))

from nicegui import ui, app
# from app.database.db import init_db, seed_db  <-- REMOVED (Legacy)
from server.app.database.db import init_server_db, seed_server_db # <-- NEW (Server)
from server.app.services.ai_brain import AIBrainService
from client_app.app.services.extraction_service import ExtractionService
from client_app.app.core.rpa_executor import RPAExecutor
from client_app.app.core.state import state
import logging

class NotFoundFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "not found" not in record.getMessage()

logging.getLogger("nicegui").addFilter(NotFoundFilter())

# Import pages

from client_app.app.ui.extraction_page import extraction_page_content
import asyncio
import os
from client_app.app.ui.playwright_wizard import ensure_playwright_ready_on_startup
from client_app.app.ui.connections_page import connections_page_content
from client_app.app.ui.logs_page import logs_page_content

# [FIX] Enable text selection in Native Mode (Desktop)
ui.add_head_html('''
<style>
    body {
        user-select: text !important;
        -webkit-user-select: text !important;
    }
</style>
''', shared=True)

# Serve uploads
app.add_static_files('/uploads', 'data/uploads')

# Register API Routers
from server.app.api.v1.brain import router as brain_router
from server.app.routers.library_router import router as library_router

app.include_router(brain_router, prefix="/api")
app.include_router(library_router, prefix="/api")

from server.app.routers.auth_router import router as auth_router
app.include_router(auth_router, prefix="/api/v1")

from server.app.routers.telemetry_router import router as telemetry_router
app.include_router(telemetry_router, prefix="/api")

# --- STARTUP ---
# --- STARTUP ---
@app.on_startup
async def startup_sequence():
    # 0. Suppress Windows IOCP errors (Benign connection resets)
    if sys.platform == 'win32':
        loop = asyncio.get_running_loop()
        def custom_handler(loop, context):
            msg = context.get("exception", context.get("message"))
            if "WinError 10054" in str(msg):
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(custom_handler)

    print("[STARTUP] Iniciando Automatia...")
    
    # 1. Initialize DB
    # 1. Initialize Server DB
    await init_server_db()
    from server.app.database.seeds import seed_all as seed_server_all
    await seed_server_all() # Populate defaults (AI Configs, Multitenancy, Prompts, Tiers)
    
    # 1.1 Seed RPA Prompts (Covered by seed_server_all which calls seed_system_prompts)
    # The function init_rpa_prompts does not exist in server.app.database.seeds
    # and sys_clarification_rpa is already in seeds_prompts.py
    # so we skip this explicit step.
    
    
    # 1.2 Seed Multitenancy Defaults (Partner/Client) - Covered by seed_server_all
    # from server.app.database.seeds_multitenancy import seed_multitenancy_defaults
    # await seed_multitenancy_defaults()

    # 1.2 Initialize & Seed Client DB (Local)
    from client_app.app.database.db import init_client_db, seed_client_db
    await init_client_db()
    await seed_client_db()
    
    print("[OK] Base de Datos Inicializada y Poblada")

    # 1.3 Initialize Security Service (Prompt 1 - Offline Policy)
    print("[STARTUP] Initializing Security Service...")
    from client_app.app.services.security_service import SecurityService
    from client_app.app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    
    # Use a dedicated session for startup security sync
    async with AsyncSession(client_engine) as session:
        security_service = SecurityService(session)
        await security_service.initialize_security()
    print("[OK] Security Service Initialized")
    
    # 2. Dependency Injection
    state.brain = AIBrainService()
    state.rpa = RPAExecutor(brain_service=state.brain)
    import logging
    state.extractor = ExtractionService(brain=state.brain, logger=logging.getLogger("ExtractionService"))
    print("[OK] Servicios Inyectados (Brain -> RPA/Extractor)")

    # 3. Startup Tasks
    if os.environ.get('AUTOMATIA_ENV') != 'test':
        print("[STARTUP] Migrating API keys from .env...")
        from client_app.app.services.api_key_service import migrate_api_keys_from_env
        await migrate_api_keys_from_env()

        print("[STARTUP] Refreshing AI model cache...")
        from server.app.services.model_fetcher import refresh_model_cache
        await refresh_model_cache()

        print("[STARTUP] Updating model prices...")
        from server.app.services.pricing_service import update_prices_from_openrouter
        await update_prices_from_openrouter()

        # Start background scheduler for periodic model refresh
        print("[STARTUP] Starting background scheduler...")
        from server.app.services.scheduler_service import scheduler_service
        scheduler_started = await scheduler_service.start()
        if scheduler_started:
            print("[OK] Background scheduler started")
        else:
            print("[INFO] Background scheduler is disabled")

        # Auto-start MailWatcher if configured
        print("[STARTUP] Checking MailWatcher auto-start...")
        from client_app.app.services.mail_watcher_service import mail_watcher_service
        from client_app.app.database.models import MailWatcherState
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine

        async with AsyncSession(client_engine) as session:
            watcher_state = await session.get(MailWatcherState, 1)

            if watcher_state and watcher_state.auto_start:
                config = await mail_watcher_service.load_config()
                if config:
                    print("[STARTUP] Auto-starting MailWatcher...")
                    success, msg = await mail_watcher_service.start_watcher(config, auto_start=True)
                    if success:
                        print("[OK] MailWatcher started successfully")
                    else:
                        print(f"[ERROR] Failed to start MailWatcher: {msg}")
                else:
                    print("[WARNING] MailWatcher auto-start enabled but no configuration found")
            else:
                print("[INFO] MailWatcher auto-start not enabled")

        # Auto-start FolderWatchers if configured
        print("[STARTUP] Checking FolderWatcher auto-start...")
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        # Create a wrapper for WorkflowEngine that manages sessions automatically
        # This is needed because FolderWatcher runs in background and needs fresh sessions
        class AutoSessionWorkflowEngine:
            async def execute_flow(self, *args, **kwargs):
                 from sqlmodel.ext.asyncio.session import AsyncSession
                 from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
                 # Use local import to avoid circular dep or early init issues
                 from client_app.app.database.db import client_engine
                 
                 async with AsyncSession(client_engine) as session:
                     engine = WorkflowEngine(session)
                     return await engine.execute_flow(*args, **kwargs)

        # Inject execution engine
        # We use the wrapper to ensure thread safety and session management
        wrapper_engine = AutoSessionWorkflowEngine()
        folder_watcher_service.set_workflow_engine(wrapper_engine)
        state.workflow_engine = wrapper_engine # Store for other uses

        # Start all with auto_start=True
        folder_started_count = await folder_watcher_service.start_all_autostart()
        if folder_started_count > 0:
            print(f"[OK] FolderWatcher auto-started {folder_started_count} monitors")
        else:
            print("[INFO] No FolderWatchers configured for auto-start")

        # Start heartbeat
        await folder_watcher_service.start_heartbeat()

        # Schedule file cleanup in background (runs after delay if retention period passed)
        print("[STARTUP] Scheduling file cleanup check...")
        from client_app.app.services.cleanup_service import cleanup_service
        await cleanup_service.schedule_startup_cleanup()

        # START WORKFLOW SCHEDULER
        print("[STARTUP] Starting Workflow Scheduler...")
        from client_app.app.services.workflow_scheduler_service import workflow_scheduler
        await workflow_scheduler.start()
        print("[OK] Workflow Scheduler initialized")
    else:
        print("[TEST] Background services disabled in TEST environment")

# --- LAYOUT ---
# Layout Refactored to separate module
from client_app.app.ui.main_layout import main_layout

from client_app.app.ui.rpa_page import rpa_page_content

# --- PAGES ---

# --- ADMIN ROUTES (REFACTORED) ---
from server.app.ui.admin_layout import AdminContext, admin_layout
from server.app.ui.admin_dashboard import admin_dashboard_content
from server.app.ui.admin_partners import admin_partners_content
from server.app.ui.admin_clients import admin_clients_content
from server.app.ui.admin_licenses import admin_licenses_content
from server.app.ui.admin_security import admin_security_content
from server.app.ui.admin_ai import admin_ai_content
from server.app.ui.admin_prompts import admin_prompts_content
from server.app.ui.admin_analytics import admin_analytics_content
from server.app.ui.admin_library import admin_library_content # [FIX] Add Import

async def get_admin_context() -> AdminContext:
    """Mock Auth for SuperAdmin."""
    return await AdminContext.from_dev_mode()

@ui.page('/admin')
def admin_root():
    # Redirect root admin to dashboard
    ui.navigate.to('/admin/dashboard')

@ui.page('/admin/dashboard')
async def admin_dashboard_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_dashboard_content(), ctx)

@ui.page('/admin/partners')
async def admin_partners_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_partners_content(), ctx)

@ui.page('/admin/clients')
async def admin_clients_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_clients_content(), ctx)

@ui.page('/admin/licenses')
async def admin_licenses_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_licenses_content(), ctx)

@ui.page('/admin/security')
async def admin_security_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_security_content(), ctx)

@ui.page('/admin/ai-config')
async def admin_ai_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_ai_content(), ctx)

@ui.page('/admin/prompts')
async def admin_prompts_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_prompts_content(), ctx)

@ui.page('/admin/analytics')
async def admin_analytics_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_analytics_content(ctx), ctx)

@ui.page('/admin/library')
async def admin_library_page():
    ctx = await get_admin_context()
    admin_layout(lambda: admin_library_content(ctx), ctx)

from client_app.app.ui.dashboard_page import dashboard_page_content

@ui.page('/')
def dashboard_page():
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        dashboard_page_content()

@ui.page('/rpa')
async def rpa_page(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        await rpa_page_content(initial_mode=initial_mode, atom_id=atom_id)

@ui.page('/documents')
async def documents_page(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    main_layout()
    await extraction_page_content(initial_mode=initial_mode, atom_id=atom_id)

from client_app.app.ui.client_admin_page import client_admin_page_content

@ui.page('/config')
def config_page(tab: str = 'General'):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        client_admin_page_content(tab=tab)

from client_app.app.ui.logs_page import logs_page_content

@ui.page('/logs')
def logs_page():
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        logs_page_content()

from client_app.app.ui.flows_page import flows_page_content
@ui.page('/flows')
@ui.page('/flows/{flow_id}')
def flows_page(flow_id: Optional[str] = None):
    main_layout()
    flows_page_content(flow_id)

from client_app.app.ui.etl_page import etl_page_content

@ui.page('/etl')
async def etl_page(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    main_layout()
    await etl_page_content(initial_mode=initial_mode, atom_id=atom_id)

from client_app.app.ui.anonymizer_page import anonymizer_page_content

@ui.page('/anonymizer')
async def anonymizer_page():
    main_layout()
    await anonymizer_page_content(mode='atom')

# [FIX] Add route for Reports Designer
from client_app.app.ui.report_designer_page import report_designer_page_content

@ui.page('/reports/designer')
async def reports_designer_page(initial_mode: Optional[str] = None, atom_id: Optional[str] = None):
    main_layout(mini_sidebar=True)
    report_designer_page_content(initial_mode=initial_mode, atom_id=atom_id)

from client_app.app.ui.graphics_page import graphics_page

@ui.page('/graphics')
async def graphics_route(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    main_layout()
    await graphics_page(initial_mode=initial_mode, atom_id=atom_id)

from client_app.app.ui.llm_process_page import llm_process_page_content

@ui.page('/llm-process')
async def llm_process_route(initial_mode: Optional[str] = None, prompt_id: Optional[int] = None):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        await llm_process_page_content(prompt_id=prompt_id, initial_mode=initial_mode)


@ui.page('/connections/api')
async def api_fetch_route(initial_mode: Optional[str] = None):
    main_layout()
    from client_app.app.ui.api_fetch_page import api_fetch_page
    await api_fetch_page(initial_mode=initial_mode)

@ui.page('/connections/smtp')
async def connections_smtp_route(atom_id: Optional[int] = None):
    main_layout()
    from client_app.app.ui.smtp_page import smtp_page
    await smtp_page(atom_id=atom_id)

@ui.page('/connections/sql')
async def sql_query_route(initial_mode: Optional[str] = None):
    main_layout()
    from client_app.app.ui.sql_query_page import sql_query_page
    await sql_query_page(initial_mode=initial_mode)

@ui.page('/connections/email')
async def email_watcher_route(mode: str = 'library', watcher_id: Optional[int] = None):
    main_layout()
    from client_app.app.ui.email_watcher_page import email_watcher_page
    await email_watcher_page(mode=mode, watcher_id=watcher_id)

@ui.page('/connections/folders')
async def folder_watcher_route(mode: str = 'library', config_id: int = None):
    main_layout()
    from client_app.app.ui.folder_watcher_page import folder_watcher_page
    await folder_watcher_page(mode=mode, config_id=config_id)

# /connections/webhooks eliminado - No viable en instalaciones locales detrás de firewall

@ui.page('/mail-watcher')
def mail_watcher_page_legacy():
    # Redirect legacy route
    ui.navigate.to('/connections/email')

@ui.page('/web-watcher')
def web_watcher_page_legacy():
    """Redirige a la nueva ubicación del Monitor Web."""
    ui.navigate.to('/triggers/web-watcher')


# --- NUEVOS ÁTOMOS (Fase 2 Taxonomía) ---

# Disparadores (Unified)
@ui.page('/triggers')
async def triggers_route():
    main_layout()
    from client_app.app.ui.triggers_page import triggers_page
    await triggers_page()

@ui.page('/triggers/web-watcher')
async def web_watcher_route_new(mode: str = 'library', watcher_id: int = None):
    main_layout()
    from client_app.app.ui.web_watcher_page import web_watcher_page
    await web_watcher_page(mode=mode, watcher_id=watcher_id)

@ui.page('/triggers/scheduler')
async def scheduler_route_new(mode: str = 'library', job_id: str = None):
    main_layout()
    from client_app.app.ui.scheduler_page import scheduler_page
    await scheduler_page(mode=mode, job_id=job_id)

# Legacy Individual Routes (Removing /triggers/web-watcher, etc.)
# If internal navigation still uses them, we can keep aliases or rely on the dashboard dialogs.
# The user said no redirects needed, so we remove them to clean up.

# Entradas
@ui.page('/inputs/folder-scan')
async def folder_scan_route():
    main_layout()
    from client_app.app.ui.folder_scan_page import folder_scan_page
    await folder_scan_page()

@ui.page('/inputs/email-scan')
async def email_scan_route():
    main_layout()
    from client_app.app.ui.email_scan_page import email_scan_page
    await email_scan_page()

# Salidas
@ui.page('/outputs/archive')
async def archive_file_route():
    main_layout()
    from client_app.app.ui.archive_file_page import archive_file_page
    await archive_file_page()

# Alias para rutas de menú (según nueva taxonomía)
# Alias para rutas de menú (según nueva taxonomía) -> Eliminados al unificar

@ui.page('/inputs/sql')
async def sql_query_route_alias():
    main_layout()
    from client_app.app.ui.sql_query_page import sql_query_page
    await sql_query_page()

@ui.page('/inputs/api')
async def api_fetch_route_alias():
    main_layout()
    from client_app.app.ui.api_fetch_page import api_fetch_page
    await api_fetch_page()

@ui.page('/outputs/smtp')
async def smtp_route_alias(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    main_layout()
    from client_app.app.ui.smtp_page import smtp_page
    await smtp_page(initial_mode=initial_mode, atom_id=atom_id)

@ui.page('/outputs/sql')
async def sql_insert_route(initial_mode: Optional[str] = None):
    main_layout()
    from client_app.app.ui.sql_insert_page import sql_insert_page
    await sql_insert_page(initial_mode=initial_mode)

from client_app.app.ui.custom_script_page import custom_script_page_content

@ui.page('/custom-scripts')
async def custom_scripts_page(initial_mode: Optional[str] = None):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        await custom_script_page_content(initial_mode=initial_mode)

from client_app.app.ui.script_library_page import script_library_page_content

@ui.page('/atoms')
async def atoms_page():
    main_layout()
    await script_library_page_content()


@ui.page('/custom-scripts/new')
async def custom_scripts_wizard_page():
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        await custom_script_page_content(initial_mode='design')

@ui.page('/custom-scripts/{script_id}/run')
async def custom_scripts_run_page(script_id: int):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        # Pass script_id to load existing script for execution
        await custom_script_page_content(script_id=script_id, initial_mode='execution')

@ui.page('/custom-scripts/{script_id}/edit')
async def custom_scripts_edit_page(script_id: int):
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        # Pass script_id to load existing script for editing
        await custom_script_page_content(script_id=script_id)


@ui.page('/connections')
def connections_page():
    main_layout()
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        connections_page_content()


@ui.page('/packages')
def packages_page():
    """Redirige a /config - Paquetes ahora está en la pestaña de Configuración."""
    ui.navigate.to('/config')


# --- UTILIDADES (Direct-use tools) ---

@ui.page('/utilities/anonymizer')
async def utilities_anonymizer_route():
    main_layout()
    # Anonimizador en modo utilidad (simplificado)
    await anonymizer_page_content(mode='utility')


# --- ATOM CONFIGURATION PAGES ---
# Import to register @ui.page decorated routes
from client_app.app.ui.pdf_tools_atom_page import pdf_tools_new_route, pdf_tools_edit_route, pdf_tools_utility_route
from client_app.app.ui.docs_page import docs_page_content
# --- PARTNER ROUTES (P25/P26) ---
from server.app.ui.partner_layout import PartnerContext, partner_layout
from server.app.ui.partner_dashboard import partner_dashboard_content
from server.app.ui.partner_clients import partner_clients_content
from server.app.ui.partner_licenses import partner_licenses_content
from server.app.ui.partner_security import partner_security_content
from server.app.ui.partner_scripts import partner_scripts_content
from server.app.ui.partner_billing import partner_billing_content
from server.app.ui.partner_login import partner_login_content
from server.app.ui.partner_library import partner_library_content # [FIX] Add Import
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine

async def get_partner_context() -> PartnerContext:
    """
    Helper para obtener contexto.
    En Dev, fuerza 'partner_001'. En Prod (P27), leera token de sesion.
    """
    # TODO: Implementar lectura de cookie/token real para P27
    # token = app.storage.user.get('partner_token')
    
    # Fallback / Dev Mode
    async with AsyncSession(server_engine) as session:
        ctx = await PartnerContext.from_dev_mode("partner_dev", session)
        return ctx

@ui.page('/partner')
def partner_root():
    ui.navigate.to('/partner/dashboard')

@ui.page('/partner/login')
def partner_login_page():
    partner_login_content()

@ui.page('/partner/dashboard')
async def partner_dashboard_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_dashboard_content(ctx), ctx)

@ui.page('/partner/clients')
async def partner_clients_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_clients_content(ctx), ctx)

@ui.page('/partner/licenses')
async def partner_licenses_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_licenses_content(ctx), ctx)

@ui.page('/partner/security')
async def partner_security_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_security_content(ctx), ctx)

@ui.page('/partner/scripts')
async def partner_scripts_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_scripts_content(ctx), ctx)

@ui.page('/partner/billing')
async def partner_billing_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_billing_content(ctx), ctx)

@ui.page('/partner/library')
async def partner_library_page():
    ctx = await get_partner_context()
    if not ctx:
        ui.navigate.to('/partner/login')
        return
    partner_layout(lambda: partner_library_content(ctx), ctx)

@ui.page('/partner/logout')
async def partner_logout_route():
    # app.storage.user['partner_token'] = None
    ui.navigate.to('/')




# --- SHUTDOWN ---
@app.on_shutdown
async def shutdown_db():
    print("[SHUTDOWN] Stopping FolderWatchers...")
    try:
        from client_app.app.services.folder_watcher_service import folder_watcher_service
        await folder_watcher_service.stop_all()
        await folder_watcher_service.stop_heartbeat()

        from client_app.app.services.workflow_scheduler_service import workflow_scheduler
        await workflow_scheduler.stop()
    except Exception as e:
        print(f"[ERROR] Stopping FolderWatchers: {e}")

    print("[SHUTDOWN] Stopping Sandbox ProcessPool...")
    try:
        from client_app.app.services.sandbox_service import sandbox_service
        sandbox_service.shutdown()
        print("[OK] Sandbox ProcessPool closed")
    except Exception as e:
        print(f"[ERROR] Sandbox shutdown: {e}")

    print("[SHUTDOWN] Desconectando Base de Datos...")
    try:
        from client_app.app.database.db import client_engine
        from server.app.database.db import server_engine
        
        # Dispose engines with timeout to avoid hanging
        await asyncio.wait_for(client_engine.dispose(), timeout=2.0)
        await asyncio.wait_for(server_engine.dispose(), timeout=2.0)
        print("[OK] Bases de datos cerradas correctamente")
    except asyncio.TimeoutError:
        print("[WARNING] Database disposal timed out (expected on shutdown)")
    except RuntimeError as e:
        # Suppress "Event loop is closed" errors during shutdown
        if "Event loop is closed" not in str(e):
            print(f"[ERROR] Database shutdown: {e}")
    except Exception as e:
        print(f"[ERROR] Database shutdown: {e}")

# --- MAIN ---
if __name__ in {"__main__", "__mp_main__"}:
    mode = os.environ.get('AUTOMATIA_MODE', 'native')
    is_native = mode == 'native'

    ui.run(
        title='Gov Gen AI',
        port=8080,
        reload=False,
        dark=False,
        show=False,             # Don't open browser tab (native window opens)
        reconnect_timeout=15.0,
        storage_secret='dev_secret_key_123',
        native=is_native,       # Controlled by env var
        window_size=(1280, 800), # Default window size
        uvicorn_reload_excludes='.servicios_generados, */.servicios_generados/*'
    )
