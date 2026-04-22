import ast
import re
from typing import List, Set, Dict, Any, Optional

class SecurityException(Exception):
    """Excepción lanzada cuando el código viola las políticas de seguridad."""
    pass

# Whitelist (scripts en sandbox) - EXTENDIDA
SAFE_IMPORTS = {
    # Data processing
    'pandas', 'numpy', 'openpyxl', 'xlrd', 'csv',
    # PDF
    'fitz', 'pdfplumber', 'PyPDF2',
    # Text/Regex
    're', 'json', 'string', 'unicodedata',
    # Math/Numbers
    'math', 'decimal', 'statistics',
    # Date/Time
    'datetime', 'time', 'calendar',
    # Collections/Iterators
    'collections', 'itertools', 'functools',
    # Typing
    'typing', 'typing_extensions',
    # I/O seguro (solo lectura en jail)
    'io', 'pathlib',
    # Otros seguros
    'hashlib', 'base64', 'uuid', 'enum', 'dataclasses',
    'matplotlib', 'seaborn',
}

# Prohibidos (import) explícitos para feedback claro
FORBIDDEN_IMPORTS = {
    'os', 'sys', 'subprocess', 'shutil', 'platform',
    'importlib', 'socket', 'ssl', 'http', 'urllib', 'requests', 'httpx',
    'ctypes', 'cffi', 'pickle', 'marshal', 'shelve',
    'code', 'codeop', 'pty', 'tty',
    'multiprocessing', 'threading', 'concurrent',
    'ast', 'dis', 'inspect', 'gc', 'traceback',
    'builtins', 'types', 'nicegui', 'fastapi', 'uvicorn'
}

# Prohibidos (llamadas)
FORBIDDEN_CALLS = {
    'eval', 'exec', 'compile', 'input',
    'vars', 'locals', 'globals', 'dir',
    '__import__', 'open',  # print opcional según contexto, aquí lo bloqueamos por defecto si se usa como función call dangerous
    'getattr', 'setattr', 'delattr',  # cuando se usan con strings dinámicos
    'type', 'object.__new__', 'help', 'copyright', 'credits', 'license', 'quit', 'exit'
}

# Prohibidos (atributos/dunders)
FORBIDDEN_ATTRS = {
    '__class__', '__mro__', '__bases__', '__subclasses__',
    '__globals__', '__code__', '__closure__', '__dict__',
    '__getattribute__', '__setattr__', '__delattr__',
    '__builtins__', '__loader__', '__spec__',
    '__reduce__', '__reduce_ex__',  # pickle hooks
}

class SecurityAuditor(ast.NodeVisitor):
    """
    Analizador estático de AST endurecido.
    Usa whitelist para imports y blacklist para llamadas/atributos peligrosos.
    """
    def __init__(self):
        """
        Inicializa el auditor y prepara las estructuras para acumular hallazgos.
        """
        self.unsafe_imports: Set[str] = set() # Acumulará imports detectados que no sean safe
        self.errors: List[str] = []
        self.blocked_nodes: List[Dict[str, Any]] = []

    def _add_error(self, node: ast.AST, rule: str, detail: str, is_critical: bool = True):
        """
        Registra una violación de seguridad detectada en el AST.

        Args:
            node: Nodo del AST donde se detectó el problema.
            rule: Tipo de regla violada (ej: 'forbidden-import').
            detail: Detalle específico (ej: nombre del módulo o función).
            is_critical: Si la violación debe considerarse crítica.
        """
        line = getattr(node, 'lineno', 0)
        col = getattr(node, 'col_offset', 0)
        msg = f"{rule}: {detail} en línea {line}"
        self.errors.append(msg)
        self.blocked_nodes.append({
            'type': type(node).__name__,
            'loc': f"L{line}:C{col}",
            'rule': rule,
            'detail': detail
        })
        if rule == 'forbidden-import':
            self.unsafe_imports.add(detail)

    def visit_Import(self, node: ast.Import):
        """Audita sentencias 'import module'."""
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module not in SAFE_IMPORTS:
                # Si está explícitamente prohibido o simplemente no está en whitelist
                if base_module in FORBIDDEN_IMPORTS:
                     self._add_error(node, 'forbidden-import', base_module)
                else: 
                     # Por defecto whitelisting: si no es safe, es forbidden
                     self._add_error(node, 'forbidden-import', base_module)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Audita sentencias 'from module import name'."""
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module not in SAFE_IMPORTS:
                 self._add_error(node, 'forbidden-import', base_module)
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        """Audita el acceso a atributos y métodos (detección de dunders peligrosos)."""
        # Detectar acceso a atributos/dunders prohibidos
        if node.attr in FORBIDDEN_ATTRS:
             self._add_error(node, 'forbidden-attr', node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Audita llamadas a funciones y métodos contra la lista negra."""
        # Detectar llamadas a funciones prohibidas
        
        # Caso 1: Llamada directa a función (ej: open(), eval())
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in FORBIDDEN_CALLS:
                 self._add_error(node, 'forbidden-call', func_name)

        # Caso 2: Llamada a método/atributo (ej: fitz.open(), os.system())
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
            # Sub-caso especial: 'open' de librerías permitidas
            if func_name == 'open':
                whitelist_open = {'fitz', 'pdfplumber', 'gzip', 'tarfile', 'Image'} # Image de PIL
                caller_id = None
                if isinstance(node.func.value, ast.Name):
                    caller_id = node.func.value.id
                
                if caller_id not in whitelist_open:
                     self._add_error(node, 'forbidden-call', f"{caller_id or '?'}.open")
            
            # Sub-caso especial: 'compile' de re
            elif func_name == 'compile':
                whitelist_compile = {'re'}
                caller_id = None
                if isinstance(node.func.value, ast.Name):
                    caller_id = node.func.value.id
                
                if caller_id not in whitelist_compile:
                     self._add_error(node, 'forbidden-call', f"{caller_id or '?'}.compile")
            
            # Sub-caso especial: 'system' siempre peligroso si es de os/subprocess
            elif func_name == 'system':
                 self._add_error(node, 'forbidden-call', 'system')

            # Chequeo genérico de llamadas prohibidas usadas como métodos
            elif func_name in FORBIDDEN_CALLS:
                 # Algunas palabras comunes pueden ser métodos seguros (ej: 'open' ya filtrado arriba, 'type' en dataframe)
                 # 'type' es call prohibido built-in, pero df.type podría ser válido?
                 # Por seguridad AST hardening, bloqueamos si coincide con forbidden calls estricto
                 if func_name not in ['print']: # print method podría ser válido en algunos objetos customs, pero print func no.
                     self._add_error(node, 'forbidden-call-method', func_name)

        self.generic_visit(node)

def audit_code(code: str) -> Dict[str, Any]:
    """
    Audita el código Python generado y devuelve clasificación de riesgo.
    Retorna: {'status': 'SAFE'|'WARNING'|'CRITICAL', 'reasons': [...], 'blocked_nodes': [...]}
    """
    result = {'status': 'SAFE', 'reasons': [], 'blocked_nodes': []}
    
    # 1. Regex Metrics (CRITICAL) - Fail Fast
    if re.search(r'[a-zA-Z]:\\\\', code) or re.search(r'[a-zA-Z]:/', code):
         result['status'] = 'CRITICAL'
         result['reasons'].append("Ruta absoluta de Windows detectada (CRITICAL).")
         return result
         
    if re.search(r'[\'"]/(home|etc|usr|var|root|tmp|proc|sys)(?:/|[\'"])', code):
         result['status'] = 'CRITICAL'
         result['reasons'].append("Ruta absoluta de Sistema Linux detectada (CRITICAL).")
         return result

    # 2. AST Parsing
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result['status'] = 'CRITICAL'
        result['reasons'].append(f"Error de Sintaxis irrecuperable: {e}")
        return result

    # 3. AST Auditing
    auditor = SecurityAuditor()
    auditor.visit(tree)

    if auditor.errors:
        result['reasons'] = auditor.errors
        result['blocked_nodes'] = auditor.blocked_nodes
        
        # Determine Status
        # En hardening estricto, cualquier violación detectada es CRITICAL o WARNING
        # Imports prohibidos -> CRITICAL
        # Forbidden calls/attrs -> CRITICAL
        
        has_critical = False
        for node in auditor.blocked_nodes:
            # Asumimos todo violación de nuestra política estricta es CRÍTICA
            # excepto quizás 'print' si quisiéramos relajarlo, pero en P16 pedimos hardening.
            has_critical = True 
        
        result['status'] = 'CRITICAL' if has_critical else 'WARNING'
    
    return result

# Legacy wrapper
def validate_code_ast(code: str) -> bool:
    """
    Función de compatibilidad que lanza SecurityException si el código no es seguro.
    
    Args:
        code: Código Python a validar.
    
    Raises:
        SecurityException: Si se encuentra alguna violación crítica de seguridad.
    """
    audit = audit_code(code)
    if audit['status'] in ('CRITICAL', 'WARNING'):
        raise SecurityException("\n".join(audit['reasons']))
    return True
