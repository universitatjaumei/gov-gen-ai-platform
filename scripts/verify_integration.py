# Verificar que shared funciona desde ambos lados
try:
    from automatia_shared.enums import TaskStatus
    from automatia_shared.dtos import FlowSpec
    print("✅ automatia_shared imports OK")
except ImportError as e:
    print(f"❌ automatia_shared import FAILED: {e}")
    exit(1)

# Verificar imports de server
try:
    from server.app.database.models import AIConfig
    print("✅ server imports OK")
except ImportError as e:
    print(f"❌ server import FAILED: {e}")
    exit(1)

# Verificar imports de client
try:
    from client_app.app.database.models import RpaPlaybook
    print("✅ client_app imports OK")
except ImportError as e:
    print(f"❌ client_app import FAILED: {e}")
    exit(1)

print('Integración OK: Todos los paquetes se importan correctamente')
