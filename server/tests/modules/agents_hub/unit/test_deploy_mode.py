import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI


def test_deploy_mode_invalid_raises():
    with patch.dict(os.environ, {"DEPLOY_MODE": "foo"}):
        import importlib
        with pytest.raises(RuntimeError, match="Invalid DEPLOY_MODE: foo"):
            import server.app.main
            importlib.reload(server.app.main)

def test_deploy_mode_cloud_excludes_edge_routers():
    with patch.dict(os.environ, {"DEPLOY_MODE": "cloud"}):
        import importlib
        import server.app.main
        importlib.reload(server.app.main)
        
        # Check if cloud routers exist and edge routers do not
        routes = [r.path for r in server.app.main.app.routes]
        assert any(p.startswith("/api/v1/hub/chatbots") for p in routes)
        assert not any(p == "/api/v1/hub/chat" for p in routes)

def test_deploy_mode_edge_excludes_cloud_routers():
    with patch.dict(os.environ, {"DEPLOY_MODE": "edge"}):
        import importlib
        import server.app.main
        importlib.reload(server.app.main)
        
        routes = [r.path for r in server.app.main.app.routes]
        assert any(p.startswith("/api/v1/hub/chat") for p in routes)
        assert not any(p.startswith("/api/v1/hub/chatbots") for p in routes)

def test_default_deploy_mode_registers_all_routers():
    with patch.dict(os.environ, clear=True):
        import importlib
        import server.app.main
        importlib.reload(server.app.main)
        
        routes = [r.path for r in server.app.main.app.routes]
        assert any(p.startswith("/api/v1/hub/chatbots") for p in routes)
        assert any(p.startswith("/api/v1/hub/chat") for p in routes)
