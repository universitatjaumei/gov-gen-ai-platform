
"""
Layout base para el portal de SuperAdministración.

Proporciona la estructura común (sidebar, header, breadcrumbs) para todas 
las páginas del panel de administración global, gestionando el estado de 
autenticación y la inyección de contenido.
"""
from nicegui import ui, app
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state

@dataclass
class AdminContext:
    """
    Contexto de ejecución y estado para el SuperAdmin.
    
    Almacena información sobre el rol, estado de sesión y rutas de 
    redirección necesarias para la navegación protegida.
    """
    role: str = "SUPERADMIN"
    is_authenticated: bool = True
    redirect_url: str = "/admin/login"

    @classmethod
    async def from_dev_mode(cls) -> "AdminContext":
        """
        MODO DESARROLLO: Autenticacion simulada como SuperAdmin.
        """
        return cls(is_authenticated=True)

    def get_header_text(self) -> str:
        return "Panel de Administración del Servidor"


def get_admin_sidebar_items() -> List[Dict[str, Any]]:
    """Items del menu lateral de Admin."""
    t = state.i18n.t
    return [
        {"label": t('admin.menu_dashboard'), "icon": "dashboard", "route": "/admin/dashboard"},
        {"label": t('admin.menu_partners'), "icon": "business", "route": "/admin/partners"},
        {"label": t('admin.menu_clients'), "icon": "badge", "route": "/admin/clients"},
        {"label": t('admin.menu_licenses'), "icon": "verified_user", "route": "/admin/licenses"},
        {"label": t('admin.menu_security'), "icon": "security", "route": "/admin/security"},
        {"label": "Observabilidad", "icon": "analytics", "route": "/admin/analytics"},
        {"label": "Templates Globales", "icon": "public", "route": "/admin/library"},
        {"label": t('admin.menu_ai_config'), "icon": "settings", "route": "/admin/ai-config"},
        {"label": t('admin.menu_prompts'), "icon": "psychology", "route": "/admin/prompts"},
    ]

def generate_breadcrumb(path: str) -> List[Dict[str, str]]:
    """Generar breadcrumb desde la ruta."""
    t = state.i18n.t
    clean_path = path.split('?')[0]
    segments = clean_path.strip("/").split("/")
    breadcrumb = []

    labels = {
        # "admin": "Admin", # Removed to prevent redundant breadcrumb
        "dashboard": t('admin.menu_dashboard'),
        "partners": t('admin.menu_partners'),
        "clients": t('admin.menu_clients'),
        "licenses": t('admin.menu_licenses'),
        "security": t('admin.menu_security'),
        "ai-config": t('admin.menu_ai_config'),
        "prompts": t('admin.menu_prompts'),
    }

    current_path = ""
    for seg in segments:
        current_path += f"/{seg}" # Always update path
        if seg in labels:
            breadcrumb.append({
                "label": labels[seg],
                "path": current_path
            })

    return breadcrumb

def admin_layout(content_fn: Callable, ctx: AdminContext):
    """
    Envoltorio visual que aplica el diseño de administración a una función de contenido.

    Args:
        content_fn: Función que renderiza el contenido específico de la página.
        ctx: Contexto de administración con el estado del usuario.
    """
    if not ctx.is_authenticated:
        ui.navigate.to(ctx.redirect_url)
        return

    # --- LAYOUT ---
    with ui.header().classes('bg-slate-900 text-white shadow-md items-center'):
        with ui.row().classes('w-full items-center justify-between px-4'):
            ui.label(ctx.get_header_text()).classes('text-xl font-bold tracking-tight')

            with ui.row().classes('items-center gap-4'):
                # Language Selector
                ui.select(
                    options=['es', 'ca'],
                    value=state.i18n.locale,
                    on_change=lambda e: (state.i18n.set_locale(e.value), ui.navigate.reload())
                ).props('dense outlined options-dense').classes('bg-white text-black w-24 rounded px-2 text-xs')

                ui.label("SuperAdmin").classes('text-sm')
                ui.button(icon='logout', on_click=lambda: ui.navigate.to('/')).props('flat round color=white')

    with ui.row().classes('w-full h-[calc(100vh-64px)]'):
        # --- SIDEBAR ---
        with ui.column().classes('w-64 h-full bg-slate-50 flex flex-col p-0 gap-0 border-r border-gray-200'):
            ui.label("MENU ADMIN").classes('text-gray-500 text-xs font-bold px-4 py-2 uppercase tracking-wider mt-2')
            
            for item in get_admin_sidebar_items():
                with ui.row().classes('w-full h-12 px-4 cursor-pointer text-slate-700 hover:bg-slate-200 items-center gap-3 transition-colors').on('click', lambda r=item["route"]: ui.navigate.to(r)):
                    ui.icon(item["icon"]).classes('text-slate-700')
                    ui.label(item["label"]).classes('text-sm font-medium')
            
            # Spacer to push any bottom content
            ui.space()

        # --- MAIN CONTENT ---
        with ui.column().classes('flex-1 h-full p-6 bg-white overflow-y-auto'):
            # Breadcrumb
            with ui.row().classes('mb-4 gap-2 text-sm text-gray-500'):
                bc = generate_breadcrumb(app.storage.browser.get('current_path', '/admin'))
                for i, crumb in enumerate(bc):
                    if i > 0:
                        ui.label('/').classes('text-gray-300')
                    ui.link(crumb["label"], crumb["path"]).classes('hover:text-indigo-600')

            # Content
            content_fn()
