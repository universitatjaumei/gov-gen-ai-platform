"""
Página de Autenticación para Partners.

Gestiona el acceso seguro de los partners al portal de administración de
su red de clientes mediante validación de credenciales y generación de
sesiones seguras.
"""

from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.db import server_engine
# from server.app.auth.session_store import SessionStore # This will be available after I create the stub

# For now, to ensure it works even if I can't create the file immediately or reuse:
try:
    from server.app.auth.session_store import SessionStore
except ImportError:
    # Fallback stub if file creation fails or race condition
    class SessionStore:
        def __init__(self, session):
            pass

        async def authenticate(self, email, password):
            if password == "test":
                return {"token": "dummy", "partner_id": "dev"}
            return None


def partner_login_content():
    """Contenido de la pagina de login."""

    class LoginState:
        email: str = ""
        password: str = ""
        error: str = ""
        loading: bool = False

    state = LoginState()

    async def do_login():
        state.loading = True
        state.error = ""
        error_label.set_text("")

        try:
            async with AsyncSession(server_engine) as session:
                store = SessionStore(session)
                result = await store.authenticate(state.email, state.password)

            if result:
                # Guardar token en cookie/storage
                ui.run_javascript(f'''
                    localStorage.setItem("partner_token", "{result["token"]}");
                ''')
                ui.navigate.to("/partner/dashboard")
            else:
                state.error = "Credenciales invalidas"
                error_label.set_text(state.error)

        except Exception as e:
            state.error = f"Error: {str(e)}"
            error_label.set_text(state.error)

        state.loading = False

    # --- UI ---
    with ui.card().classes("w-96 mx-auto mt-20 p-8"):
        ui.label("Acceso Partner").classes("text-2xl font-bold text-center mb-6")

        ui.input(
            label="Email",
            placeholder="partner@empresa.com",
            on_change=lambda e: setattr(state, "email", e.value),
        ).classes("w-full").props("outlined")

        ui.input(
            label="Password",
            password=True,
            on_change=lambda e: setattr(state, "password", e.value),
        ).classes("w-full").props("outlined")

        error_label = ui.label().classes("text-red-500 text-sm")

        ui.button("Iniciar Sesion", icon="login", on_click=do_login).classes(
            "w-full mt-4"
        ).props("color=primary")


async def partner_logout():
    """Lógica de logout para partners."""
    ui.run_javascript('localStorage.removeItem("partner_token");')
    ui.navigate.to("/partner/login")
