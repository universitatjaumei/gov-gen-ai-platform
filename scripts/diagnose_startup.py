import sys
import asyncio
from pathlib import Path

# Add shared library to path
_project_root = Path(__file__).parent
sys.path.insert(0, str(_project_root / 'shared'))

async def test_startup():
    """Test each startup step individually to find the blocking point."""
    
    print("=" * 60)
    print("DIAGNOSTIC: Testing Startup Sequence")
    print("=" * 60)
    
    try:
        print("\n[1/10] Testing DB imports...")
        from app.database.db import init_db, seed_db
        print("✓ DB imports successful")
        
        print("\n[2/10] Testing service imports...")
        from app.services.ai_brain import AIBrainService
        from app.services.extraction_service import ExtractionService
        from app.core.rpa_executor import RPAExecutor
        from app.core.state import state
        print("✓ Service imports successful")
        
        print("\n[3/10] Initializing database...")
        await init_db()
        print("✓ Database initialized")
        
        print("\n[4/10] Seeding database...")
        await seed_db()
        print("✓ Database seeded")
        
        print("\n[5/10] Seeding RPA prompts...")
        from app.database.seeds import init_rpa_prompts
        await init_rpa_prompts()
        print("✓ RPA prompts seeded")
        
        print("\n[6/10] Seeding multitenancy defaults...")
        from app.database.seeds_multitenancy import seed_multitenancy_defaults
        await seed_multitenancy_defaults()
        print("✓ Multitenancy defaults seeded")
        
        print("\n[7/10] Initializing client DB...")
        from client_app.app.database.db import init_client_db, seed_client_db
        await init_client_db()
        await seed_client_db()
        print("✓ Client DB initialized and seeded")
        
        print("\n[8/10] Migrating API keys...")
        from app.services.api_key_service import migrate_api_keys_from_env
        await migrate_api_keys_from_env()
        print("✓ API keys migrated")
        
        print("\n[9/10] Refreshing AI model cache...")
        from app.services.model_fetcher import refresh_model_cache
        await refresh_model_cache()
        print("✓ Model cache refreshed")
        
        print("\n[10/10] Updating model prices...")
        from app.services.pricing_service import update_prices_from_openrouter
        await update_prices_from_openrouter()
        print("✓ Model prices updated")
        
        print("\n" + "=" * 60)
        print("✓ ALL STARTUP STEPS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR at current step:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_startup())
    sys.exit(0 if success else 1)
