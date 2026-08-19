import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ in {"__main__", "__mp_main__"}:
    # Import root main to trigger startup configuration and UI definition
    import main as root_main
    
    # Re-use configuration from root main
    # Ensure native matches the requirement (web mode for tests)
    import os
    mode = os.environ.get('AUTOMATIA_MODE', 'native')
    is_native = mode == 'native'
    
    from nicegui import ui
    
    # Check if ui.run was already called or needs to be called. 
    # Root main calls it under `if __name__ == "__main__"`. 
    # We must replicate the ui.run call.
    ui.run(
        title='AutomatIA',
        port=8080,
        reload=False,
        dark=False,
        show=False,
        reconnect_timeout=15.0,
        storage_secret='dev_secret_key_123',
        native=is_native, # Use the env var logic
        window_size=(1280, 800),
        uvicorn_reload_excludes='.servicios_generados, */.servicios_generados/*'
    )
