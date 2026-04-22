
import sys
import os
import asyncio
import inspect
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

# Mock dependencies that might be missing in this env
sys.modules["faker"] = MagicMock()
sys.modules["client_app.app.modules.privacy.anonymizer"] = MagicMock()
# Also mock AnonymizationContext specifically if it's imported from there
mock_anon = MagicMock()
sys.modules["client_app.app.modules.privacy.anonymizer"].AnonymizationContext = mock_anon

# Mock db session context if needed (though UI shouldn't trigger it on import)
# Mock state
sys.modules["client_app.app.core.state"] = MagicMock()


async def verify_pages():
    print("Verifying Phase 2 Pages...")
    errors = []

    # 1. Automations Selector
    try:
        from client_app.app.ui.components.automation_selector import render_automation_selector
        print("✅ automation_selector imported successfully")
    except Exception as e:
        errors.append(f"automation_selector import failed: {e}")

    # 2. RPA Page
    try:
        from client_app.app.ui.rpa_page import rpa_page_content
        print("✅ rpa_page imported successfully")
        # Check if render_automation_selector is used (static check)
        with open('client_app/app/ui/rpa_page.py', 'r', encoding='utf-8') as f:
            if 'render_automation_selector' not in f.read():
                errors.append("rpa_page.py missing render_automation_selector usage")
    except Exception as e:
        errors.append(f"rpa_page import failed: {e}")

    # 3. ETL Page
    try:
        from client_app.app.ui.etl_page import etl_page_content
        print("✅ etl_page imported successfully")
        with open('client_app/app/ui/etl_page.py', 'r', encoding='utf-8') as f:
            if 'render_automation_selector' not in f.read():
                errors.append("etl_page.py missing render_automation_selector usage")
    except Exception as e:
        errors.append(f"etl_page import failed: {e}")

    # 4. Graphics Page
    try:
        from client_app.app.ui.graphics_page import graphics_page
        print("✅ graphics_page imported successfully")
        
        # Check async definition
        if not inspect.iscoroutinefunction(graphics_page):
            errors.append("graphics_page should be async def")
            
        with open('client_app/app/ui/graphics_page.py', 'r', encoding='utf-8') as f:
            if 'render_automation_selector' not in f.read():
                errors.append("graphics_page.py missing render_automation_selector usage")

    except Exception as e:
        errors.append(f"graphics_page import failed: {e}")

    if errors:
        print("\n❌ Errors found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n✅ All pages verified successfully!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(verify_pages())
