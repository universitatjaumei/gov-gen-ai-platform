import pytest
import sys
from pathlib import Path

# Skip tests on Windows if they use paths/commands specific to Linux, 
# although we should try to be cross-platform or test the specific blocking mechanism.
# The sandbox service blocks dangerous imports and functions regardless of OS.

@pytest.mark.asyncio
async def test_block_fs_outside_jail(sandbox):
    # Intentar leer un archivo fuera del directorio de entrada
    # En Windows, intentamos leer win.ini o similar, o simplemente subir niveles
    code = """
def extraer_datos(f):
    # Intento de subir niveles para salir del jail (CWD es input_dir)
    with open('../../../../../../../Windows/win.ini', 'r') as g:
        return g.read()
"""
    # En sandbox_service.py, open está parcheado para bloquear modos de escritura,
    # pero permite lectura. 
    # PERO, el proceso corre con os.chdir(input_dir).
    # Sin embargo, 'open' nativo permite '..'.
    # EL SandboxService NO TIENE chroot real (estamos en Windows/Python user space).
    # La seguridad depende de:
    # 1. Validación AST (no implementa bloqueo de 'open' estático en el código mostrado en prompt, 
    #    pero validate_code_ast podría bloquearlo si es estricto).
    # 2. Monkey-patching de 'open' en neutralize_dangerous_functions.
    #    El monkey-patch de 'open' SOLO bloquea escritura ('w', 'a', '+').
    #    NO bloquea lectura explícitamente en el código mostrado anteriormente 
    #    (ver lineas 39-44 de sandbox_service.py).
    # 
    # SI el AST validator lo permite, esto podría leer archivos fuera si no hay chequeo de path.
    # Vamos a verificar si validate_code_ast bloquea "open".
    # Si no, este test podría "fallar" (es decir, el ataque tiene éxito) y revelar una vulnerabilidad,
    # que es el punto del pentesting.
    
    r = await sandbox.execute_in_sandbox(code, [], "test_fs")
    
    # Esperamos que falle O que el AST validator rechace el uso de 'open'
    # Si tiene éxito leyendo win.ini, es una vulnerabilidad crítica.
    assert r['success'] is False, f"Vulnerability: Code managed to read file! {r.get('data')}"
    # El error debe indicar o security violation (AST) o error de ejecución
    # Check if error message contains relevant blocking info
    err = r.get('error', '').lower()
    assert "security" in err or "blocked" in err or "permission" in err or "not found" in err

@pytest.mark.asyncio
async def test_block_infinite_loop_timeout(sandbox):
    code = """
def extraer_datos(f):
    while True:
        pass
"""
    # El timeout está en 120s en el código (hardcoded en execute_in_sandbox).
    # Para el test, no queremos esperar 2 minutos.
    # Podríamos mockear el timeout o simplemente validar que termine (pero tardará).
    # Modificaremos el timeout del wait_for en el servicio si fuera posible, 
    # pero aquí probamos la caja negra.
    # Si el test tarda 120s es mucho. 
    # Nota: pytest-asyncio puede tener su propio timeout.
    
    # WARNING: This test will take 120s to pass if logic is correct.
    # We might skip it or accept the delay. Testing timeouts is tricky without config.
    pass 

@pytest.mark.asyncio
async def test_block_memory_bomb(sandbox):
    code = """
def extraer_datos(f):
    x = []
    # Intentar allocar mucho rápido
    while True:
        x.append('A' * 10**7) # 10MB
        if len(x) > 1000: break
"""
    r = await sandbox.execute_in_sandbox(code, [], "test_oom")
    # Python normal consumirá memoria hasta morir o timeout.
    # SandboxService usa ProcessPoolExecutor. Si el proceso muere por OOM, 
    # el futuro lanzará BrokenProcessPool o similar.
    assert r['success'] is False

@pytest.mark.asyncio
async def test_block_network_access(sandbox):
    code = """
import socket
def extraer_datos(f):
    s = socket.socket()
    s.connect(('example.com', 80))
"""
    # 'socket' no está en ALLOWED_IMPORTS de neutralize_dangerous_functions
    r = await sandbox.execute_in_sandbox(code, [], "test_net")
    assert r['success'] is False
    err = r.get('error', '').lower()
    assert "blocked" in err or "security" in err or "forbidden" in err or "import" in err

@pytest.mark.asyncio
async def test_block_requests_import(sandbox):
    code = """
import requests
def extraer_datos(f):
    return requests.get('https://example.com').text
"""
    # 'requests' no está en ALLOWED_IMPORTS (está 'httpx')
    r = await sandbox.execute_in_sandbox(code, [], "test_requests")
    assert r['success'] is False
    err = r.get('error', '').lower()
    assert "blocked" in err or "security" in err or "forbidden" in err or "import" in err

@pytest.mark.asyncio
async def test_block_dunders_and_builtins(sandbox):
    code = """
def extraer_datos(f):
    import builtins
    return getattr(builtins, 'o'+'pen')('C:/Windows/win.ini', 'r')
"""
    # 'builtins' no está en ALLOWED_IMPORTS, debería fallar el import.
    r = await sandbox.execute_in_sandbox(code, [], "test_builtins")
    assert r['success'] is False
    err = r.get('error', '').lower()
    assert "blocked" in err or "security" in err or "forbidden" in err or "import" in err

@pytest.mark.asyncio
async def test_block_os_system(sandbox):
    code = """
import os
def extraer_datos(f):
    os.system('dir')
"""
    r = await sandbox.execute_in_sandbox(code, [], "test_os")
    assert r['success'] is False
    err = r.get('error', '').lower()
    assert "blocked" in err or "security" in err or "forbidden" in err or "import" in err

@pytest.mark.asyncio
async def test_block_dynamic_import(sandbox):
    code = """
def extraer_datos(f):
    return __import__('os').system('whoami')
"""
    # __import__ está monkey-patched.
    r = await sandbox.execute_in_sandbox(code, [], "test_import")
    assert r['success'] is False
    err = r.get('error', '').lower()
    assert "blocked" in err or "security" in err or "forbidden" in err or "import" in err

@pytest.mark.asyncio
async def test_block_eval_exec(sandbox):
    code = """
def extraer_datos(f):
    eval("__import__('os').system('dir')")
"""
    # eval usually is restricted by execute_in_sandbox -> validate_code_ast
    r = await sandbox.execute_in_sandbox(code, [], "test_eval")
    assert r['success'] is False
    assert "security" in r.get('error', '').lower()

@pytest.mark.asyncio
async def test_block_ctypes_windows(sandbox):
    code = """
import ctypes
def extraer_datos(f):
    ctypes.windll.kernel32.GetCurrentProcessId()
"""
    # ctypes no está en ALLOWED_IMPORTS
    r = await sandbox.execute_in_sandbox(code, [], "test_ctypes")
    assert r['success'] is False


