"""
Connections Hub - Centro de acceso rápido a tipos de átomos.

Proporciona tarjetas de acceso rápido organizadas por la nueva taxonomía
de 4 capas funcionales (Disparadores, Entradas, Procesadores, Salidas).

Refactorizado como parte de la Fase 3 del Plan de Taxonomía.
"""
from nicegui import ui
from client_app.app.core.state import state


def connections_page_content():
    t = state.i18n.t

    with ui.column().classes('w-full items-center gap-8 py-8'):
        with ui.column().classes('items-center text-center max-w-2xl'):
            ui.label('Centro de Conexiones').classes('text-4xl font-black text-slate-800 tracking-tight')
            ui.label(
                'Gestiona tus fuentes de datos, disparadores y salidas en un solo lugar. '
                'Selecciona un tipo de acción para comenzar.'
            ).classes('text-slate-500 text-lg mt-2')

        # === DISPARADORES ===
        ui.label('Disparadores').classes('text-2xl font-bold text-slate-700 mt-4')
        with ui.row().classes('text-slate-500 text-sm items-center gap-2 -mt-2'):
            ui.icon('bolt', size='sm')
            ui.label('Inician flujos automáticamente cuando ocurre un evento')

        with ui.grid(columns=4).classes('w-full max-w-5xl gap-6'):
            # Folder Watcher
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-orange-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/connections/folders')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('folder', size='3rem').classes('text-orange-500 group-hover:scale-110 transition-transform')
                    ui.label('Monitor de Carpeta').classes('text-xl font-bold')
                    ui.label('Vigila cambios en carpetas locales o de red.').classes('text-center text-sm text-slate-400')

            # Email Watcher
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-blue-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/connections/email')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('mark_email_unread', size='3rem').classes('text-blue-500 group-hover:scale-110 transition-transform')
                    ui.label('Monitor de Email').classes('text-xl font-bold')
                    ui.label('Monitorea buzones IMAP para disparar flujos.').classes('text-center text-sm text-slate-400')

            # Web Watcher
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-green-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/triggers/web-watcher')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('public', size='3rem').classes('text-green-500 group-hover:scale-110 transition-transform')
                    ui.label('Monitor Web').classes('text-xl font-bold')
                    ui.label('Detecta cambios en páginas web.').classes('text-center text-sm text-slate-400')

            # Scheduler
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-amber-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/triggers/scheduler')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('schedule', size='3rem').classes('text-amber-500 group-hover:scale-110 transition-transform')
                    ui.label('Programador').classes('text-xl font-bold')
                    ui.label('Ejecuta flujos en horarios programados.').classes('text-center text-sm text-slate-400')

        # === ENTRADAS ===
        ui.label('Entradas').classes('text-2xl font-bold text-slate-700 mt-8')
        with ui.row().classes('text-slate-500 text-sm items-center gap-2 -mt-2'):
            ui.icon('login', size='sm')
            ui.label('Obtienen datos de fuentes externas')

        with ui.grid(columns=4).classes('w-full max-w-5xl gap-6'):
            # SQL Query
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-blue-grey-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/inputs/sql')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('storage', size='3rem').classes('text-blue-grey-500 group-hover:scale-110 transition-transform')
                    ui.label('Consulta SQL').classes('text-xl font-bold')
                    ui.label('Acceso directo a bases de datos.').classes('text-center text-sm text-slate-400')

            # API Fetch
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-cyan-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/inputs/api')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('api', size='3rem').classes('text-cyan-500 group-hover:scale-110 transition-transform')
                    ui.label('API Fetch').classes('text-xl font-bold')
                    ui.label('Consulta servicios REST/JSON.').classes('text-center text-sm text-slate-400')

            # Folder Scan
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-orange-400 overflow-hidden group').on('click', lambda: ui.navigate.to('/inputs/folder-scan')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('folder_open', size='3rem').classes('text-orange-400 group-hover:scale-110 transition-transform')
                    ui.label('Escaneo Carpeta').classes('text-xl font-bold')
                    ui.label('Lista archivos por patrón.').classes('text-center text-sm text-slate-400')

            # Email Scan
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-indigo-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/inputs/email-scan')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('attach_email', size='3rem').classes('text-indigo-500 group-hover:scale-110 transition-transform')
                    ui.label('Recolector Email').classes('text-xl font-bold')
                    ui.label('Busca y descarga adjuntos.').classes('text-center text-sm text-slate-400')

        # === PROCESADORES (selección rápida) ===
        ui.label('Procesadores').classes('text-2xl font-bold text-slate-700 mt-8')
        with ui.row().classes('text-slate-500 text-sm items-center gap-2 -mt-2'):
            ui.icon('psychology', size='sm')
            ui.label('Transforman datos en visualizaciones o informes')

        with ui.grid(columns=2).classes('w-full max-w-5xl gap-6'):
            # Graphics
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-pink-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/graphics')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('bar_chart', size='3rem').classes('text-pink-500 group-hover:scale-110 transition-transform')
                    ui.label('Gráficos').classes('text-xl font-bold')
                    ui.label('Genera visualizaciones de datos.').classes('text-center text-sm text-slate-400')

            # Reports
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-purple-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/reports/designer')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('description', size='3rem').classes('text-purple-500 group-hover:scale-110 transition-transform')
                    ui.label('Generador Informes').classes('text-xl font-bold')
                    ui.label('Crea documentos con datos y gráficos.').classes('text-center text-sm text-slate-400')

        # === SALIDAS ===
        ui.label('Salidas').classes('text-2xl font-bold text-slate-700 mt-8')
        with ui.row().classes('text-slate-500 text-sm items-center gap-2 -mt-2'):
            ui.icon('logout', size='sm')
            ui.label('Envían o almacenan los resultados del procesamiento')

        with ui.grid(columns=3).classes('w-full max-w-5xl gap-6'):
            # SMTP
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-teal-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/connections/smtp')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('send', size='3rem').classes('text-teal-500 group-hover:scale-110 transition-transform')
                    ui.label('Email (SMTP)').classes('text-xl font-bold')
                    ui.label('Envía notificaciones por correo.').classes('text-center text-sm text-slate-400')

            # API POST
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-cyan-500 overflow-hidden group').on('click', lambda: ui.navigate.to('/inputs/api')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('cloud_upload', size='3rem').classes('text-cyan-500 group-hover:scale-110 transition-transform')
                    ui.label('API (POST)').classes('text-xl font-bold')
                    ui.label('Envía datos a servicios REST.').classes('text-center text-sm text-slate-400')

            # Archive File
            with ui.card().classes('hover:shadow-xl transition-all cursor-pointer p-6 border-t-4 border-teal-600 overflow-hidden group').on('click', lambda: ui.navigate.to('/outputs/archive')):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('save_alt', size='3rem').classes('text-teal-600 group-hover:scale-110 transition-transform')
                    ui.label('Archivar Resultado').classes('text-xl font-bold')
                    ui.label('Guarda archivos en destino.').classes('text-center text-sm text-slate-400')
