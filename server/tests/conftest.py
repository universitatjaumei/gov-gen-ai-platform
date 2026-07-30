import sys
from pathlib import Path

# Add project root to path
# __file__ is server/tests/conftest.py → parent.parent.parent is the repo root
sys.path.append(str(Path(__file__).parent.parent.parent))

# La política de event loops se declara en pyproject.toml
# (asyncio_default_fixture_loop_scope = "function"), no aquí: el override de la fixture
# `event_loop` está deprecado en pytest-asyncio 1.x y lo vigila
# tests/infra/test_suite_hygiene.py.
