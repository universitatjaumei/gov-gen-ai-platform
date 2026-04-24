import os
import re
from pathlib import Path

files = [
    r"server\tests\modules\agents_hub\unit\test_chat_endpoint.py",
    r"server\tests\modules\agents_hub\e2e\conftest.py",
    r"server\tests\modules\agents_hub\e2e\test_chat_flow.py",
    r"server\tests\modules\agents_hub\unit\test_export_endpoint.py",
    r"server\app\modules\agents_hub\services\feedback_service.py",
    r"server\app\routers\hub_chatbots_router.py",
    r"server\tests\modules\agents_hub\integration\test_database_models.py",
    r"server\app\modules\agents_hub\ingestion\watcher.py",
    r"server\app\modules\agents_hub\services\prompt_service.py",
    r"server\app\routers\hub_clients_router.py",
    r"server\app\modules\agents_hub\services\model_factory.py",
    r"server\app\modules\agents_hub\services\retriever.py",
    r"server\migrations\env.py",
    r"server\tests\modules\agents_hub\integration\test_full_pipeline.py",
    r"server\app\modules\agents_hub\database\seeds.py",
    r"server\tests\modules\agents_hub\integration\test_retriever.py",
    r"server\app\api\v1\hub_chat.py",
    r"server\app\api\v1\hub_tasks.py",
]

config_models = {"HubClient", "HubChatbot", "HubLLMConfig", "HubPromptTemplate"}
operational_models = {"HubDocumentChunk", "HubInteraction", "HubIngestionJob"}
base_models = {"HubBase"}

import_regex = re.compile(r'from\s+server\.app\.modules\.agents_hub\.database\.models\s+import\s+(?:\((.*?)\)|(.*?))(?=\n[^\s]|\n\n|\Z)', re.DOTALL)

for fpath in files:
    py_file = Path(fpath)
    if not py_file.exists():
        continue
    content = py_file.read_text(encoding="utf-8")
    if "agents_hub.database.models" not in content:
        continue
    
    def replacer(match):
        imported_str = match.group(1) or match.group(2)
        # remove newlines and spaces, split by comma
        imported_items = [x.strip() for x in imported_str.replace('\n', '').split(',')]
        imported_items = [x for x in imported_items if x]
        
        c_models = []
        o_models = []
        b_models = []
        
        for item in imported_items:
            if item in config_models:
                c_models.append(item)
            elif item in operational_models:
                o_models.append(item)
            elif item in base_models:
                b_models.append("HubConfigBase")
                b_models.append("HubOperationalBase")
        
        new_imports = []
        if b_models:
            new_imports.append(f"from server.app.modules.agents_hub.database.base import {', '.join(sorted(set(b_models)))}")
        if c_models:
            new_imports.append(f"from server.app.modules.agents_hub.database.config_models import {', '.join(sorted(c_models))}")
        if o_models:
            new_imports.append(f"from server.app.modules.agents_hub.database.operational_models import {', '.join(sorted(o_models))}")
            
        return "\n".join(new_imports)

    new_content = import_regex.sub(replacer, content)
    new_content = new_content.replace("from server.app.modules.agents_hub.database.models import HubBase  # noqa: F401", "from server.app.modules.agents_hub.database.base import HubConfigBase, HubOperationalBase  # noqa: F401")
    py_file.write_text(new_content, encoding="utf-8")
    print(f"Updated {py_file}")
