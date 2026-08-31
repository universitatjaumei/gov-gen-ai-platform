"""La dimensión del vector de fragmentos vuelve a 1024, que es la que usa el código.

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-08-31

**Un defecto que sólo aparecía en instalaciones nuevas, y por eso llevaba meses invisible.**

La primera migración del esquema deja la columna en 1536:

    a1b2c3d4e5f6_hub_schema.py:133
    ALTER TABLE hub_document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)

y **ninguna migración posterior la corrige**. Pero el modelo declara `Vector(1024)`
(`operational_models.py:375`), y una migración posterior crea `hub_crawled_pages.page_embedding`
como `Vector(1024)`: la convención del proyecto son 1024 —la dimensión de BGE-M3— y ese 1536 es
un residuo.

Consecuencia: **una base creada con `alembic upgrade head` tiene una columna en la que la
aplicación no puede escribir.** La primera ingesta falla con «expected 1536 dimensions, not
1024». Afecta a cualquier despliegue nuevo, incluido un edge node.

Por qué no se veía: la base de desarrollo está en 1024 porque su tabla no nació de la cadena de
migraciones, y el test de instalación limpia comprueba que las columnas **existan** pero no su
tipo. Apareció al restaurar el corpus en el despliegue de producción, que es la primera base de
este proyecto creada de verdad sólo con migraciones.

**Es condicional a propósito.** Sólo altera donde la dimensión no es ya 1024, así que en una base
correcta no toca nada y no pierde vectores. Donde está en 1536 los datos no pueden ser válidos
—la aplicación nunca ha podido escribir ahí—, así que anularlos no destruye nada real.
"""
from alembic import op

revision = "e2b3c4d5f6a7"
down_revision = "d1a2b3c4e5f6"
branch_labels = None
depends_on = None


_A_1024 = """
DO $$
DECLARE tipo text;
BEGIN
    SELECT format_type(atttypid, atttypmod) INTO tipo
      FROM pg_attribute
     WHERE attrelid = 'hub_document_chunks'::regclass
       AND attname = 'embedding';

    IF tipo IS DISTINCT FROM 'vector(1024)' THEN
        RAISE NOTICE 'embedding estaba en %, se pasa a vector(1024)', tipo;
        ALTER TABLE hub_document_chunks
              ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024);
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(_A_1024)


def downgrade() -> None:
    # No se vuelve a 1536 a propósito: era el defecto. Volver dejaría la base otra vez en un
    # estado en el que la aplicación no puede escribir, que no es un estado al que nadie quiera
    # regresar.
    pass
