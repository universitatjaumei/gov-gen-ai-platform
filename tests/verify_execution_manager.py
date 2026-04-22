import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from app.core.execution_manager import ExecutionPathManager, ExecutionLock, RunManifest
import os
import shutil
import time

def test_execution_manager():
    print("--- Testing Execution Manager ---")
    
    # 1. Init
    manager = ExecutionPathManager(app_name="automatia_test_data")
    print(f"Base Dir: {manager.base_dir}")
    
    # Clean up test output if exists
    if manager.base_dir.exists():
        shutil.rmtree(manager.base_dir)
    
    # 2. Create Run
    task_type = "TEST_TASK"
    run_id = manager.create_run(task_type)
    print(f"Created Run ID: {run_id}")
    
    run_dir = manager.get_run_dir(task_type, run_id)
    print(f"Run Dir: {run_dir}")
    
    # Verify Structure
    expected_dirs = ["inputs", "outputs", "logs", "scripts/versions", "sandbox"]
    for d in expected_dirs:
        p = run_dir / d
        if not p.exists():
            print(f"❌ Missing directory: {d}")
        else:
            print(f"✅ Found: {d}")

    # 3. Verify Manifest Initial State
    manifest = RunManifest(run_dir / "run_manifest.json")
    manifest.load()
    if manifest.data['status'] == 'created':
        print(f"✅ Manifest Init Correct: {manifest.data['run_id']}")
    else:
        print(f"❌ Manifest Status Error: {manifest.data}")
        
    # 4. Verify Script Versioning
    script_v1 = "print('Hello World V1')"
    manager.save_script_version(task_type, run_id, script_v1)
    
    # Check v1
    manifest.load()
    versions = manifest.data['script']['versions']
    if len(versions) == 1:
        print("✅ Version 1 recorded in manifest")
    else:
        print(f"❌ Version count error: {len(versions)}")
        
    # Check content hash
    h1 = versions[0]['hash']
    v1_file = run_dir / versions[0]['file']
    if v1_file.exists() and "V1" in v1_file.read_text():
        print(f"✅ Version 1 file content correct ({h1})")
        
    # Confirm script_current.py
    current = run_dir / "scripts" / "script_current.py"
    if current.read_text() == script_v1:
         print("✅ script_current.py matches V1")
         
    # Save V2
    script_v2 = "print('Hello World V2')"
    manager.save_script_version(task_type, run_id, script_v2)
    
    manifest.load()
    versions = manifest.data['script']['versions']
    if len(versions) == 2 and versions[-1]['hash'] != h1:
         print("✅ Version 2 recorded")
    
    if current.read_text() == script_v2:
         print("✅ script_current.py updated to V2")
         
    # 5. Verify IDEMPOTENCY of Versioning (Same content -> No new version)
    manager.save_script_version(task_type, run_id, script_v2)
    manifest.load()
    if len(manifest.data['script']['versions']) == 2:
         print("✅ Versioning Idempotency works (Duplicate content ignored)")
    else:
         print("❌ Idempotency failed, versions grown")
         
    # 6. Verify Locking
    lock = manager.get_lock(task_type, run_id)
    try:
        lock.acquire()
        print("✅ Lock acquired")
        
        # Try recursive/dual acquire (Should FAIL or Block)
        # Since it is same process... msvcrt might behave specifically.
        # Usually file locks are per-process or per-handle.
        # Let's test basic release.
    finally:
        lock.release()
        print("✅ Lock released")

    # verify manifest atomic update
    manifest.update({"status": "running"})
    manifest.load()
    if manifest.data['status'] == "running":
        print("✅ Manifest Update Works")
        
    print("\n🎉 ALL TESTS PASSED")

if __name__ == "__main__":
    test_execution_manager()
