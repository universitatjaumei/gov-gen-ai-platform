"""
Migración: Añadir soporte para contratos de datos en AtomRegistry.

Añade campos:
- subtype (TEXT, nullable)
- input_contract (TEXT, nullable)
- output_contract (TEXT, nullable)
- dependencies (JSON, default [])

Data Contracts Fase 1, Prompt 1.

Uso manual para SQLite existente:
    python -m client_app.app.database.migrations.add_atom_contracts

Para nuevas instalaciones: SQLModel.metadata.create_all() ya incluye estos campos.
"""
import sqlite3
import json
from pathlib import Path


def get_db_path() -> Path:
    """Obtener ruta de la base de datos local."""
    # Ruta por defecto en desarrollo
    return Path("data/client_local.db")


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Verificar si una columna existe en una tabla."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def upgrade(db_path: Path = None):
    """Añadir campos de contratos a atom_registry."""
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        print(f"Base de datos no encontrada: {db_path}")
        print("La migración se aplicará automáticamente al crear la tabla.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Verificar si la tabla existe
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='atom_registry'"
        )
        if not cursor.fetchone():
            print("Tabla atom_registry no existe. Se creará con los nuevos campos.")
            return

        migrations = []

        # Añadir columna subtype
        if not column_exists(cursor, 'atom_registry', 'subtype'):
            cursor.execute('ALTER TABLE atom_registry ADD COLUMN subtype TEXT')
            migrations.append('subtype')

        # Añadir columna input_contract
        if not column_exists(cursor, 'atom_registry', 'input_contract'):
            cursor.execute('ALTER TABLE atom_registry ADD COLUMN input_contract TEXT')
            migrations.append('input_contract')

        # Añadir columna output_contract
        if not column_exists(cursor, 'atom_registry', 'output_contract'):
            cursor.execute('ALTER TABLE atom_registry ADD COLUMN output_contract TEXT')
            migrations.append('output_contract')

        # Añadir columna dependencies
        if not column_exists(cursor, 'atom_registry', 'dependencies'):
            cursor.execute("ALTER TABLE atom_registry ADD COLUMN dependencies TEXT DEFAULT '[]'")
            migrations.append('dependencies')

        conn.commit()

        if migrations:
            print(f"Migración completada. Columnas añadidas: {', '.join(migrations)}")
        else:
            print("Todas las columnas ya existen. No se realizaron cambios.")

    except Exception as e:
        conn.rollback()
        print(f"Error en migración: {e}")
        raise
    finally:
        conn.close()


def downgrade(db_path: Path = None):
    """
    Revertir cambios (SQLite no soporta DROP COLUMN directamente).

    Para revertir en SQLite se necesita recrear la tabla sin las columnas.
    Este es un proceso destructivo que solo debe hacerse en desarrollo.
    """
    print("ADVERTENCIA: SQLite no soporta DROP COLUMN nativamente.")
    print("Para revertir, recree la base de datos o use una versión anterior del schema.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
