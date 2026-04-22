"""
Migración: Extensión de ReportTemplate para informes interactivos.
"""
from sqlalchemy import text


def upgrade(connection):
    """Añadir campos nuevos a report_templates."""

    # Verificar si la tabla existe
    result = connection.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='report_templates'"
    ))

    if not result.fetchone():
        # Crear tabla completa si no existe
        connection.execute(text("""
            CREATE TABLE report_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                structure TEXT DEFAULT '{"blocks": []}',
                input_schema TEXT,
                style_config TEXT,
                preview_data TEXT,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                version TEXT DEFAULT '1.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                -- Legacy fields included for compatibility
                format TEXT DEFAULT 'pdf',
                template_type TEXT DEFAULT 'builtin',
                data_schema TEXT
            )
        """))
        connection.execute(text(
            "CREATE INDEX idx_report_templates_name ON report_templates(name)"
        ))
    else:
        # Añadir campos faltantes
        existing_columns = [row[1] for row in connection.execute(
            text("PRAGMA table_info(report_templates)")
        ).fetchall()]

        new_columns = {
            "structure": "TEXT DEFAULT '{\"blocks\": []}'",
            "input_schema": "TEXT",
            "style_config": "TEXT",
            "preview_data": "TEXT",
            "category": "TEXT DEFAULT 'general'",
            "tags": "TEXT DEFAULT '[]'",
            "is_active": "INTEGER DEFAULT 1",
            "version": "TEXT DEFAULT '1.0'",
            # Ensure legacy fields exist if not
            "format": "TEXT DEFAULT 'pdf'",
            "template_type": "TEXT DEFAULT 'builtin'",
            "data_schema": "TEXT",
            "created_by": "TEXT"
        }

        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                connection.execute(text(
                    f"ALTER TABLE report_templates ADD COLUMN {col_name} {col_def}"
                ))


def downgrade(connection):
    """Rollback: SQLite no soporta DROP COLUMN fácilmente."""
    pass
