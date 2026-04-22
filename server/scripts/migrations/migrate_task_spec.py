"""
Migración: Añadir campos de Contrato de Datos a TaskSpec
Fecha: 2026-02-02
Dependencia: Prompt 5 (Actualización de DTO)
"""
import ast
import re
import json
from typing import List, Dict, Any
from sqlmodel import Session, select, text
from shared.automatia_shared.dtos import TaskSpec

def extract_inputs_from_code(code: str) -> List[str]:
    """Intenta extraer los parámetros de una función Python."""
    if not code:
        return []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in ['transform', 'execute', 'run', 'main']:
                    return [arg.arg for arg in node.args.args if arg.arg != 'self']
    except SyntaxError:
        match = re.search(r'def\s+\w+\s*\(([^)]+)\)', code)
        if match:
            params = match.group(1).split(',')
            return [p.split(':')[0].strip() for p in params if p.strip()]
    return []

def extract_outputs_from_code(code: str) -> List[str]:
    """Intenta extraer las claves del diccionario retornado."""
    if not code:
        return []
    try:
        # Simple regex heuristic for return {'key': val}
        # Matches strict dictionary returns commonly used in the platform
        matches = re.findall(r"['\"](\w+)['\"]\s*:", code)
        # Filter commonly used non-output keys if necessary, but for now return all found keys
        # limiting scope to lines starting with return might be safer but regex is limited.
        # Let's try to parse AST if possible, otherwise fallback.
        tree = ast.parse(code)
        for node in ast.walk(tree):
             if isinstance(node, ast.Return):
                 if isinstance(node.value, ast.Dict):
                     return [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    except Exception:
        pass
    return []

def migrate_up(session: Session):
    """Actualiza el esquema y los datos."""
    # 1. Schema Update (SQLite hack for missing ALTER COLUMN support in some versions, 
    # but here we behave as if adding columns is enough or assuming ORM handles creation if table missing)
    # In a real scenario with Alembic, this would be an alembic revision.
    # Here we manually ensure columns exist for existing rows if we were running raw SQL.
    # Since we use SQLModel, we assume the valid schema is defined in code.
    # This function focuses on DATA MIGRATION (Inference).
    
    tasks = session.exec(select(TaskSpec)).all()
    print(f"Migrating {len(tasks)} tasks...")
    
    for task in tasks:
        dirty = False
        
        # Initialize defaults if None (SQLModel might return None for new nullable columns)
        if task.inputs is None:
            task.inputs = []
            dirty = True
        if task.outputs is None:
            task.outputs = []
            dirty = True
        if task.metadata is None: 
            task.metadata = {}
            dirty = True
            
        # Infer from script if Custom Script
        if task.type == 'CUSTOM_SCRIPT' and hasattr(task, 'script_code') and task.script_code:
            inferred_inputs = extract_inputs_from_code(task.script_code)
            inferred_outputs = extract_outputs_from_code(task.script_code)
            
            if inferred_inputs and not task.inputs:
                task.inputs = inferred_inputs
                dirty = True
            if inferred_outputs and not task.outputs:
                task.outputs = inferred_outputs
                dirty = True
                
        if dirty:
            session.add(task)
            
    session.commit()
    print("Migration completed.")

def migrate_down(session: Session):
    """Revert data changes (Clear fields)."""
    tasks = session.exec(select(TaskSpec)).all()
    for task in tasks:
        task.inputs = []
        task.outputs = []
        task.metadata = {}
        session.add(task)
    session.commit()
    print("Rollback completed.")
