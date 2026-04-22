import asyncio
import sys
import os
import json

# Ensure app is in path
sys.path.append(os.getcwd())

# We test the Service as the entry point to ensure DB lookup works
from app.services.ai_brain import AIBrainService
from app.database.db import seed_db

async def main():
    print("🧪 Testing AIBrainService.filter_irrelevant_data...")
    
    # 1. Ensure DB has the seed (service_id="sys_utility_noise_filter")
    print("🌱 Seeding DB for test...")
    await seed_db()
    
    brain = AIBrainService()
    
    # Scenario: User wants "Total Invoice", but data has noise.
    raw_data = {
        "Total Invoice": "150.00",
        "Date": "2023-10-01",
        "PageInfo": "1 of 5",
        "ServerMeta": "X-123", 
        "Noise": "This is footer text"
    }
    
    user_definition = "Solo quiero el Total y la Fecha."
    
    print(f"Input Data: {raw_data}")
    print(f"User Intent: {user_definition}")
    
    try:
        # We assume the default 'sys_utility_noise_filter' service ID is used
        result = await brain.clean_data_noise(
            raw_data=raw_data,
            user_definition=user_definition
        )
        
        print("\n✅ Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if "relevantes" in result:
             rel = result['relevantes']
             print(f"Relevantes: {rel}")
             if "Total Invoice" in str(rel) and "ServerMeta" not in str(rel):
                 print("✅ PASS: Noise successfully filtered out.")
             else:
                 print("⚠️ ALERT: Filter might be too loose or strict.")
        else:
             print("❌ FAIL: Structure 'relevantes' not found. LLM might have failed JSON format.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
