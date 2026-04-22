import asyncio
import sys
import subprocess
import logging
from pathlib import Path
from nicegui import ui, app, run

# Sentinel file to mark successful installation
SENTINEL_FILE = Path("data/.playwright_installed")

logger = logging.getLogger(__name__)

def is_playwright_installed() -> bool:
    """Check if the sentinel file exists."""
    return SENTINEL_FILE.exists()

def mark_playwright_installed():
    """Create the sentinel file."""
    SENTINEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL_FILE.touch()

async def check_browser_status() -> bool:
    """
    Try to launch chromium headless to verify if browsers are actually installed.
    Returns True if successful, False otherwise.
    """
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            await browser.close()
        return True
    except Exception as e:
        logger.warning(f"Playwright browser check failed: {e}")
        return False

async def ensure_playwright_ready_on_startup():
    """
    Entry point to be called from main.py on startup.
    Checks if Playwright is ready. If not, shows the wizard dialog.
    """
    # 1. Bypass if sentinel exists (Fast check)
    if is_playwright_installed():
        return

    # 2. Bypass if user skipped this session
    if app.storage.user.get('playwright_setup_skip'):
        return

    # 3. Real check (slower)
    logger.info("Checking Playwright status...")
    if await check_browser_status():
        mark_playwright_installed()
        return

    # 4. If we are here, we need to install
    show_playwright_wizard_dialog()

def show_playwright_wizard_dialog():
    """Display the installation wizard dialog."""
    
    # helper for i18n
    def t(key):
        return app.storage.user.get('i18n_t', lambda k: k)(key)

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl p-6'):
        # Header
        ui.label(t('playwright_title')).classes('text-xl font-bold mb-2')
        ui.label(t('playwright_desc')).classes('text-gray-600 mb-4')
        
        # Options
        ui.label(t('playwright_browsers')).classes('font-bold mt-2')
        chk_chromium = ui.checkbox(t('playwright_chromium'), value=True).props('disable') # Always required
        chk_firefox = ui.checkbox(t('playwright_firefox'), value=False)
        chk_webkit = ui.checkbox(t('playwright_webkit'), value=False)
        
        # System deps (Linux only)
        is_linux = sys.platform.startswith('linux')
        chk_deps = None
        if is_linux:
             chk_deps = ui.checkbox(t('playwright_with_deps'), value=False).classes('mt-2 text-sm text-gray-500')

        # Logs Area
        log_area = ui.log().classes('w-full h-48 bg-gray-900 text-green-400 font-mono text-xs p-2 rounded mt-4 overflow-y-auto')
        progress = ui.linear_progress().classes('w-full mt-2').props('indeterminate').set_visibility(False)
        
        # Status Label
        status_label = ui.label("").classes('text-sm mt-2')

        # Actions
        row_actions = ui.row().classes('w-full justify-end mt-6 gap-2')
        
        async def start_install():
            # Lock UI
            btn_install.disable()
            btn_skip.disable()
            progress.set_visibility(True)
            log_area.clear()
            status_label.set_text(t('playwright_installing'))
            
            browsers = ["chromium"]
            if chk_firefox.value: browsers.append("firefox")
            if chk_webkit.value: browsers.append("webkit")
            
            with_deps = chk_deps.value if chk_deps else False
            
            # Run
            success = await run_playwright_install(browsers, with_deps, log_area)
            
            progress.set_visibility(False)
            btn_skip.enable()
            
            if success:
                status_label.set_text(t('playwright_done')).classes('text-green-600 font-bold')
                status_label.classes(remove='text-red-600')
                mark_playwright_installed()
                ui.notify(t('playwright_ready'), type='positive')
                await asyncio.sleep(2)
                dialog.close()
            else:
                status_label.set_text(t('playwright_error').format(msg="Check logs")).classes('text-red-600 font-bold')
                btn_install.enable()
                btn_install.text = t('playwright_retry')

        async def skip_install():
            app.storage.user['playwright_setup_skip'] = True
            dialog.close()

        with row_actions:
            btn_skip = ui.button(t('playwright_skip'), on_click=skip_install).props('flat color=grey')
            btn_install = ui.button(t('playwright_install'), on_click=start_install).props('color=primary')

    dialog.open()

async def run_playwright_install(browsers: list, with_deps: bool, log_widget: ui.log) -> bool:
    """
    Executes the playwright install command in a subprocess, streaming output to the log widget.
    """
    cmd = [sys.executable, "-m", "playwright", "install"] + browsers
    if with_deps and sys.platform.startswith('linux'):
        cmd.append("--with-deps")
    
    log_widget.push(f"$ {' '.join(cmd)}")
    
    try:
        # Improved approach: Use asyncio.create_subprocess_exec for better async streaming
        # This keeps us in the loop and allows UI updates.
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        check_task = asyncio.create_task(process.wait())
        
        while not process.stdout.at_eof():
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8', errors='replace').strip()
            if line:
                log_widget.push(line)
        
        await check_task
        return process.returncode == 0

    except Exception as e:
        log_widget.push(f"EXCEPTION: {str(e)}")
        return False
