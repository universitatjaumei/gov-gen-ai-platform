"""
Core utilities for AutomatIA platform.

This module contains pure utilities shared between server and client_app:
- PDF reading (reader.py, pdf_reader.py)
- Security auditing (security.py)
- Execution management (execution_manager.py)
- Data consolidation (consolidator.py)

`i18n.py` vivía aquí y **se retiró el 2026-09-04 (NIC.4)**: leía el `translations.json` de 158 KB
de la interfaz NiceGUI, que NIC.3 retiró. El i18n de la plataforma es i18next, en
`frontend/src/shared/i18n/`, y no tiene lado servidor.
"""

# Reader utilities
from automatia_shared.core.reader import (
    extraer_texto_pyMuPDF,
    extraer_texto_pdfplumber,
    extraer_texto_dual,
    obtener_texto_completo,
    extraer_texto_pymupdf_por_pag,
)

# PDF Reader class
from automatia_shared.core.pdf_reader import PdfReaderDual

# Security utilities
from automatia_shared.core.security import (
    SecurityAuditor,
    SecurityException,
    audit_code,
    validate_code_ast,
)

# Execution management
from automatia_shared.core.execution_manager import (
    ExecutionLock,
    RunManifest,
    ExecutionPathManager,
)

# Data consolidation
from automatia_shared.core.consolidator import DataConsolidator


__all__ = [
    # Reader
    "extraer_texto_pyMuPDF",
    "extraer_texto_pdfplumber",
    "extraer_texto_dual",
    "obtener_texto_completo",
    "extraer_texto_pymupdf_por_pag",
    "PdfReaderDual",
    # Security
    "SecurityAuditor",
    "SecurityException",
    "audit_code",
    "validate_code_ast",
    # Execution
    "ExecutionLock",
    "RunManifest",
    "ExecutionPathManager",
    # Consolidation
    "DataConsolidator",
]
