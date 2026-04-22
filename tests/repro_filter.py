import asyncio
import sys
import os
import json

# Ensure app is in path
sys.path.append(os.getcwd())

from app.modules.brain.extraction_strategies import filtrar_datos_irrelevantes

# Mock config
MOCK_CONFIG = {
    "provider": "openai", 
    "model_id": "gpt-4o-mini"
}

# Mock Prompt (simulating DB retrieval)
MOCK_SYSTEM_PROMPT = """
    Rol: 'Analista de Calidad de Datos'.

    Tarea: 'Clasifica el JSON entrante comparándolo con la intención del usuario: "{definicion_usuario}".'

    Salida JSON: {{'relevantes': {{...}}, 'otros_datos': {{...}}}}.

    Regla: 'Mueve a "otros_datos" lo que sea ruido, metadatos técnicos y sobretodo, campos que NO hayan sido explícitamente solicitados en la intención del usuario. Ante la duda, déjalo en "relevantes".'
    
    JSON Entrante:
    {datos_crudos}
"""

async def main():
    print("🧪 Testing filtrar_datos_irrelevantes...")
    
    # Scenario: User wants "Total Invoice", but data has "Page 1 of 5", "Printed at...", "Server ID".
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
    
    # This calls standard 'ejecutar_tarea'. Since we reuse 'debug_brain' context usually, 
    # we need to be careful if we don't have a real LLM connected or mocked.
    # Assuming 'ejecutar_tarea' works (it connects to OpenAI/Google).
    # If not, this script might fail on API key if environment not set, 
    # but 'llm_gateway' usually reads from DB or Env. 
    # Wait, 'llm_gateway' imports 'get_api_key' which reads DB.
    # So this script needs DB access IF 'ejecutar_tarea' uses it.
    # BUT 'ejecutar_tarea' logic:
    # client = _get_client(provider) -> get_api_key(provider).
    # get_api_key reads from DB (AIConfig).
    # So we need to ensure DB is accessible or seeds are there.
    # 'repro_consolidation.py' worked because it was pure logic.
    # This one touches LLM.
    
    try:
        result = await filtrar_datos_irrelevantes(
            datos_crudos=raw_data,
            definicion_usuario=user_definition,
            config=MOCK_CONFIG,
            system_prompt=MOCK_SYSTEM_PROMPT
        )
        print("\n✅ Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if "otros_datos" in result and "ServerMeta" in result["otros_datos"]:
            print("✅ Filter Success: Metadata moved to 'otros_datos'")
        else:
            print("⚠️ Filter Warning: Metadata might not have been filtered correctly (or LLM latency/mock issue).")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
