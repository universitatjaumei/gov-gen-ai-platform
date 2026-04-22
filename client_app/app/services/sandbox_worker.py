# client_app/app/services/sandbox_worker.py
"""
Lightweight worker for sandbox execution.
This module is intended to be the entry point for ProcessPoolExecutor tasks,
minimizing the import of heavy application services.
"""
import sys
import os
import importlib.util
import traceback
import builtins
import hashlib
from typing import Dict, Any, Optional, List

def neutralize_dangerous_functions():
    """
    Modifica temporalmente funciones peligrosas de Python (monkey-patching) 
    para restringir el acceso al sistema de archivos y red en el proceso hijo.
    """
    # Check if already patched to prevent recursion depth errors on worker reuse
    if getattr(builtins, "_sandbox_patched", False):
        return

    builtins._sandbox_patched = True
    original_open = builtins.open

    # 1. Bloquear open (permitir lectura segura en CWD)
    def blocked_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        is_write = 'w' in mode or 'a' in mode or '+' in mode or 'x' in mode
        
        if is_write:
             # Validate Path: Allow writing only in CWD (Jail)
             s_file = str(file)
             cwd = os.getcwd()
             
             if os.path.isabs(s_file):
                  if not os.path.normpath(s_file).startswith(cwd):
                       raise PermissionError(f"Blocked write to outside jail: {s_file}")
             else:
                  if ".." in s_file:
                       raise PermissionError(f"Blocked path traversal: {s_file}")
        
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    builtins.open = blocked_open
    
    # 2. Bloquear imports no permitidos
    ALLOWED_IMPORTS = {
        "pandas", "numpy", "json", "re", "math", 
        "datetime", "openpyxl", "fitz", "pdfplumber", "httpx",
        "typing", "uuid", "pathlib", "functools", "itertools",
        "traceback", "importlib", "collections", "contextlib",
        "operator", "keyword", "heapq", "weakref", "copy", "warnings", "abc",
        "linecache", "tokenize", "token", "concurrent", "multiprocessing", "pickle", "_pickle", "queue", "threading",
        "io", "_io", "codecs", "_codecs", "encodings",
        "matplotlib", "seaborn", "base64",
        "atexit", "cycler", "kiwisolver", "pyparsing", "dateutil", "PIL", "inspect",
        "locale", "shutil", "logging", "os",
        "pprint", "zipfile", "tarfile", "gzip",
        "subprocess", "ctypes", "stat", "tempfile", "sys",
        "packaging", "platform",
        "__future__", "numbers", "shlex", "textwrap", "time",
        "types", "struct", "ast", "urllib", "enum",
        "builtins", "warnings", "zlib", "fractions", "array", "unicodedata",
        "string", "random", "html", "unittest", "difflib", "fnmatch", "argparse", "gettext",
        "signal", "socket", "dataclasses", "plistlib", "binascii", "xml", "pyexpat", "winreg",
        "hashlib", "decimal", "calendar", "six"
    }
    
    original_import = builtins.__import__

    def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level > 0:
            if globals:
                pkg = globals.get('__package__')
                if pkg:
                    base_pkg = pkg.split(".")[0]
                    if base_pkg in ALLOWED_IMPORTS:
                         return original_import(name, globals, locals, fromlist, level)
        
        base_name = name.split(".")[0]
        if base_name in ALLOWED_IMPORTS:
            module = original_import(name, globals, locals, fromlist, level)
            if name == "matplotlib.pyplot" or (name == "matplotlib" and fromlist and "pyplot" in fromlist):
                try:
                    if hasattr(module, "pyplot"):
                         module.pyplot.show = lambda *args, **kwargs: None
                    elif hasattr(module, "show"):
                         module.show = lambda *args, **kwargs: None
                except Exception:
                    pass
            return module
        
        # Permitir modulos internos del sandbox
        if "sandbox_mod_" in name or "client_app.app.services.sandbox_service" in name or "client_app.app.services.sandbox_worker" in name:
            return original_import(name, globals, locals, fromlist, level)
            
        raise ImportError(f"Blocked import: {name}")

    builtins.__import__ = custom_import

def _infer_type(value: Any) -> str:
    """Infiere tipo de dato desde un valor."""
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        import re
        if re.match(r'\d{4}-\d{2}-\d{2}', value) or re.match(r'\d{2}/\d{2}/\d{4}', value):
            return "date"
        return "string"
    elif isinstance(value, (list, tuple)):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "string"

def _extract_execution_metadata(input_files: List[str], results: List[Dict]) -> Dict[str, Any]:
    """Extrae metadata de entrada/salida para generación de contratos."""
    metadata = {
        "input_metadata": {
            "file_count": len(input_files),
            "file_types": list(set([f.split('.')[-1] for f in input_files])),
            "detected_fields": []
        },
        "output_metadata": {
            "fields": []
        }
    }
    
    successful_results = [r for r in results if r.get('status') == 'success']
    if not successful_results:
        return metadata
    
    first_result = successful_results[0].get('data')
    if not first_result:
        return metadata
    
    if isinstance(first_result, dict):
        for key, value in first_result.items():
            field_type = _infer_type(value)
            metadata["output_metadata"]["fields"].append({
                "name": key,
                "type": field_type,
                "label": key.replace('_', ' ').title(),
                "description": f"Campo extraído: {key}"
            })
    elif isinstance(first_result, list) and first_result and isinstance(first_result[0], dict):
        for key, value in first_result[0].items():
            field_type = _infer_type(value)
            metadata["output_metadata"]["fields"].append({
                "name": key,
                "type": field_type,
                "label": key.replace('_', ' ').title(),
                "description": f"Campo extraído: {key}"
            })
    
    return metadata

def _run_jailed_process(script_path: str, input_dir: str, function_name: str, requested_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Función auxiliar que se ejecuta en un proceso separado (aislado).
    Aplica parches de seguridad, cambia el directorio de trabajo al 'jail'
    y ejecuta la función objetivo del script.
    """
    try:
        # 0. Apply Security Patches
        neutralize_dangerous_functions()

        # 1. JAIL: Change CWD to input directory
        os.chdir(input_dir)

        # 2. Add script dir to path
        script_dir = os.path.dirname(script_path)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        # 3. Load Module
        module_name = f"sandbox_mod_{os.path.basename(script_path).replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            return {"success": False, "error": f"Could not load spec from {script_path}"}

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 4. Check Function
        if not hasattr(module, function_name):
            return {"success": False, "error": f"Function '{function_name}' not found in script."}

        target_func = getattr(module, function_name)

        # 5. Execute
        if requested_files:
            target_files = [f for f in requested_files if os.path.isfile(f)]
        else:
            target_files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.endswith('.py')]

        if not target_files:
            return {"success": False, "error": "No processing files found in sandbox input."}

        batch_results = []
        for t_file in target_files:
            try:
                single_res = target_func(t_file)
                batch_results.append({
                    "filename": t_file,
                    "data": single_res,
                    "status": "success"
                })
            except Exception as item_e:
                batch_results.append({
                    "filename": t_file,
                    "error": str(item_e),
                    "status": "error"
                })

        execution_metadata = _extract_execution_metadata(target_files, batch_results)

        return {
            "success": True, 
            "data": batch_results, 
            "cwd": os.getcwd(),
            "execution_metadata": execution_metadata
        }

    except Exception as e:
        try:
            tb = traceback.format_exc()
        except:
            tb = "Traceback unavailable due to sandbox restrictions"
        return {
            "success": False,
            "error": str(e),
            "traceback": tb
        }
