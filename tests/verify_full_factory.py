import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.extraction_service import ExtractionService
from app.services.ai_brain import AIBrainService

async def test_run_factory_pipeline():
    print("🚀 Iniciando prueba completa: Run Factory Pipeline (Brain -> Sandbox -> Audit)")
    
    # 1. Setup Services
    brain = AIBrainService()
    extraction_service = ExtractionService(brain)
    
    # 2. Setup Context
    execution_id = extraction_service.path_manager.create_execution_context("TEST_FACTORY")
    input_dir = extraction_service.path_manager.get_input_dir(execution_id)
    
    print(f"📂 Execution Context: {execution_id} ({input_dir})")
    
    # 3. Copy Sample File
    sample_file = Path("data/uploads/factura_b_1.pdf")
    if not sample_file.exists():
        # Fallback if specific sample missing
        pdfs = list(Path("data/uploads").glob("*.pdf"))
        if pdfs:
            sample_file = pdfs[0]
        else:
            print("❌ No PDFs found in data/uploads for testing.")
            return

    shutil.copy2(sample_file, input_dir / sample_file.name)
    print(f"📄 Copied Sample: {sample_file.name}")

    # 4. Execute Pipeline
    print("⚙️ Ejecutando Pipeline...")
    
    def on_progress(msg):
        print(f"  [Progress] > {msg}")

    result = await extraction_service.run_factory_pipeline(
        execution_id=execution_id,
        user_feedback="Extraer número de factura y total.",
        on_progress=on_progress
    )

    # 5. Assertions
    if result.get('status') == 'success':
        print("\n✅ Pipeline Exitoso!")
        print(f"  - Code Generated: {len(result.get('code', ''))} chars")
        print(f"  - Result Data: {result.get('result')}")
        
        audit = result.get('audit')
        if audit:
             print(f"  - Audit Report Generated: Yes ({len(str(audit))} chars)")
        else:
             print("  ⚠️ Warning: No Audit Report")
             
    else:
        print(f"\n❌ Pipeline Falló: {result.get('error')}")
        print(f"Full Result: {result}")

if __name__ == "__main__":
    try:
        asyncio.run(test_run_factory_pipeline())
    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
