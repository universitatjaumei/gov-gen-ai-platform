import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
# __file__ is server/tests/conftest.py
# parent is server/tests
# parent.parent is server
# parent.parent.parent is root (AutomatIA)
sys.path.append(str(Path(__file__).parent.parent.parent))

# Also add server/ to path if needed, but root should be enough to import server.app...

@pytest.fixture(scope="session")
def event_loop():
    """Loop de eventos para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
