"""
Migración: Añadir columna error_message a ExtractionLog.

Añade campo:
- error_message (TEXT, nullable) - Mensaje de error en extracciones fallidas

Uso manual:
    python -m client_app.app.database.migrations.add_extraction_log_error_message

Para nuevas instalaciones: SQLModel.metadata.create_all() ya incluye este campo.
"""
import sqlite3
from pathlib import Path


DB_PATHS = [
    Path("data/client_local.db"),
    Path("client_local.db"),
    Path("client_app/data/client_local.db"),
    Path("client_app/app/database/data/client_local.db"),
]


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Verificar si una columna existe en una tabla."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    """Verificar si una tabla existe."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


def upgrade_db(db_path: Path) -> bool:
    """Aplicar la migración a una base de datos específica."""
    if not db_path.exists():
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if not table_exists(cursor, "extractionlog"):
            print(f"  [{db_path}] Tabla 'extractionlog' no existe. Se omite.")
            return False

        if column_exists(cursor, "extractionlog", "error_message"):
            print(f"  [{db_path}] Columna 'error_message' ya existe. No se realizaron cambios.")
            conn.close()
            return True

        cursor.execute("ALTER TABLE extractionlog ADD COLUMN error_message TEXT")
        conn.commit()
        print(f"  [{db_path}] ✅ Columna 'error_message' añadida correctamente.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"  [{db_path}] ❌ Error en migración: {e}")
        raise
    finally:
        conn.close()


def upgrade():
    """Aplicar la migración a todas las bases de datos conocidas."""
    print("Iniciando migración: add_extraction_log_error_message")
    migrated = 0
    for db_path in DB_PATHS:
        if upgrade_db(db_path):
            migrated += 1

    if migrated == 0:
        print("No se encontraron bases de datos para migrar.")
    else:
        print(f"Migración completada en {migrated} base(s) de datos.")


if __name__ == "__main__":
    upgrade()
