"""
Core utilities for AutomatIA platform.

This module contains pure utilities shared between server and client_app:
- PDF reading (reader.py, pdf_reader.py)
- Security auditing (security.py)
- Execution management (execution_manager.py)
- Internationalization (i18n.py)
- Data consolidation (consolidator.py)
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

# Internationalization
from automatia_shared.core.i18n import (
    I18nManager,
    i18n,
    t,
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
    # I18n
    "I18nManager",
    "i18n",
    "t",
    # Consolidation
    "DataConsolidator",
]
