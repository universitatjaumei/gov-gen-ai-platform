import os
from pathlib import Path

labels = {
    r"server\app\routers\hub_chatbots_router.py": "cloud",
    r"server\app\routers\hub_clients_router.py": "cloud",
    r"server\app\routers\library_router.py": "cloud",
    r"server\app\routers\auth_router.py": "cloud",
    r"server\app\api\v1\hub_chat.py": "edge",
    r"server\app\api\v1\hub_tasks.py": "edge",
    r"server\app\api\v1\ingestion.py": "edge",
    r"server\app\api\v1\hub_feedback.py": "edge",
    r"server\app\api\v1\edge_sync.py": "shared",
    r"server\app\modules\automation\__init__.py": "edge",
    r"server\app\modules\agents_hub\agent\__init__.py": "edge",
    r"server\app\modules\agents_hub\ingestion\__init__.py": "edge",
    r"server\app\modules\agents_hub\evaluation\__init__.py": "edge",
}

for fpath, label in labels.items():
    p = Path(fpath)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        content = f'"""\nDeploy: {label}\n"""\n'
        p.write_text(content, encoding="utf-8")
        continue

    content = p.read_text(encoding="utf-8")
    if "Deploy:" in content:
        continue
    
    # Insert Deploy: label into the docstring if it exists, or create one.
    if content.startswith('"""'):
        # find the end of the docstring
        end_idx = content.find('"""', 3)
        if end_idx != -1:
            new_content = content[:end_idx] + f"\n\nDeploy: {label}\n" + content[end_idx:]
            p.write_text(new_content, encoding="utf-8")
    else:
        new_content = f'"""\nDeploy: {label}\n"""\n' + content
        p.write_text(new_content, encoding="utf-8")
    print(f"Labeled {fpath} with {label}")
