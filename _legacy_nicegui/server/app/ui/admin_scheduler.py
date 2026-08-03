"""
Configuración del Programador de Tareas (Scheduler).

Permite definir la frecuencia de actualización automática del catálogo de
modelos y otros procesos en segundo plano, asegurando que la plataforma
tenga acceso a los últimos modelos de IA disponibles.
"""

from nicegui import ui
from client_app.app.core.state import state
from server.app.services.scheduler_service import scheduler_service


def admin_scheduler_content():
    """Content for the scheduler configuration page."""
    t = state.i18n.t

    ui.label(t("admin.scheduler.title")).classes(
        "text-2xl font-bold mb-6 text-slate-800"
    )

    # Status card
    status_card = ui.card().classes("w-full p-4 mb-6")

    # Configuration card
    with ui.card().classes("w-full p-4"):
        ui.label(t("admin.scheduler.config_title")).classes("text-lg font-bold mb-4")

        # State holders
        enabled_switch = {"ref": None}
        hour_select = {"ref": None}
        minute_select = {"ref": None}

        with ui.column().classes("w-full gap-4"):
            # Enable/Disable switch
            with ui.row().classes("items-center gap-4"):
                ui.label(t("admin.scheduler.enabled_label")).classes(
                    "text-sm font-medium"
                )
                enabled_switch["ref"] = ui.switch(value=True).classes("ml-auto")

            # Time selection
            with ui.row().classes("items-center gap-4 w-full"):
                ui.label(t("admin.scheduler.time_label")).classes("text-sm font-medium")

                with ui.row().classes("ml-auto items-center gap-2"):
                    hour_select["ref"] = ui.select(
                        options=[f"{h:02d}" for h in range(24)],
                        value="03",
                        label=t("admin.scheduler.hour"),
                    ).classes("w-24")

                    ui.label(":").classes("text-xl font-bold")

                    minute_select["ref"] = ui.select(
                        options=[f"{m:02d}" for m in range(0, 60, 5)],
                        value="00",
                        label=t("admin.scheduler.minute"),
                    ).classes("w-24")

            # Action buttons
            with ui.row().classes("w-full gap-4 mt-4"):

                async def save_config():
                    enabled = enabled_switch["ref"].value
                    hour = int(hour_select["ref"].value)
                    minute = int(minute_select["ref"].value)

                    await scheduler_service.update_schedule(enabled, hour, minute)
                    ui.notify(t("admin.scheduler.config_saved"), type="positive")
                    await refresh_status()

                async def run_manual_refresh():
                    ui.notify(t("admin.scheduler.manual_started"), type="info")
                    await scheduler_service.run_now()
                    ui.notify(t("admin.scheduler.manual_completed"), type="positive")
                    await refresh_status()

                ui.button(t("common.save"), icon="save", on_click=save_config).props(
                    "color=primary"
                )

                ui.button(
                    t("admin.scheduler.run_now"),
                    icon="refresh",
                    on_click=run_manual_refresh,
                ).props("color=secondary outline")

    async def refresh_status():
        """Refresh the status display."""
        status = await scheduler_service.get_status()

        status_card.clear()
        with status_card:
            ui.label(t("admin.scheduler.status_title")).classes(
                "text-lg font-bold mb-4"
            )

            with ui.grid(columns=2).classes("w-full gap-4"):
                # Status indicator
                with ui.column().classes("items-center p-4 bg-slate-50 rounded"):
                    status_color = (
                        "text-green-600" if status["running"] else "text-gray-400"
                    )
                    status_icon = "check_circle" if status["running"] else "cancel"
                    ui.icon(status_icon).classes(f"{status_color} text-4xl")
                    ui.label(
                        t("admin.scheduler.status_running")
                        if status["running"]
                        else t("admin.scheduler.status_stopped")
                    ).classes(f"{status_color} font-medium")

                # Next run info
                with ui.column().classes("items-center p-4 bg-slate-50 rounded"):
                    ui.icon("schedule").classes("text-blue-600 text-4xl")
                    if status["next_run"]:
                        from datetime import datetime

                        next_run = datetime.fromisoformat(status["next_run"])
                        ui.label(next_run.strftime("%H:%M")).classes(
                            "text-blue-600 font-bold text-xl"
                        )
                        ui.label(t("admin.scheduler.next_run")).classes(
                            "text-gray-500 text-sm"
                        )
                    else:
                        ui.label("--:--").classes("text-gray-400 font-bold text-xl")
                        ui.label(t("admin.scheduler.not_scheduled")).classes(
                            "text-gray-400 text-sm"
                        )

            # Last run info
            if status["last_run"]:
                from datetime import datetime

                last_run = datetime.fromisoformat(status["last_run"])
                ui.label(
                    f"{t('admin.scheduler.last_run')}: {last_run.strftime('%Y-%m-%d %H:%M')}"
                ).classes("text-sm text-gray-500 mt-4")

        # Update form values
        enabled_switch["ref"].value = status["enabled"]
        hour_select["ref"].value = f"{status['refresh_hour']:02d}"
        minute_select["ref"].value = f"{status['refresh_minute']:02d}"

    # Load initial status
    ui.timer(0.1, refresh_status, once=True)
