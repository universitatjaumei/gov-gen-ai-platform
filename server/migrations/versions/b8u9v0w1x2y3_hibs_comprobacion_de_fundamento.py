"""HIB.S — el interruptor de la comprobación de fundamento de la cita

El contrato de citas de HIB.0 pregunta «¿ha citado algo del conjunto recuperado?». Es una buena
pregunta: sobre el lote de 48 escenarios de Normativa rechazó 7 de los 18 negativos **sin un solo
rechazo indebido** sobre 30 contestables, mientras la puerta de calidad rechazaba **cero de 48**.
Pero se queda corta, y los 11 negativos que el asistente contesta y no debería **citan** — citan
normas de la UJI que hablan de contratos para una pregunta de contratos.

Tampoco hay atajo por el lado de la recuperación: se midieron cuatro señales y ninguna separa esos
11 de los 30 que sí debía contestar. La nota de calidad (0,643-0,787 contra 0,692-0,805, con los
fallos de mediana **más alta**), la brecha entre el primero y el segundo (0,020 contra 0,010, al
revés de lo que convendría), el número de fuentes (3 y 3), y «la mejor evidencia es un documento
vetado» (gana en 2 de 8 negativos y en 1 de 6 contestables).

**Por qué una columna y no una constante.** La comprobación cuesta una llamada al modelo por
respuesta, y el criterio de cierre del prompt exige medir la latencia del primer token **con y sin
ella**. Sin interruptor esa medición no se puede hacer. Y cuando esté decidida, seguirá haciendo
falta: no todos los asistentes tienen el mismo coste de equivocarse — un funcionario que recibe un
umbral de contratación equivocado actúa sobre él.

**Nullable, y nulo significa heredar de la plataforma.** Es la convención de la cascada: una
columna NOT NULL en el chatbot gana siempre al defecto de plataforma, y eso fue la trampa que
HIB.Q documentó y que HIB.R tuvo que rodear moviendo el defecto de la columna. Aquí no hace falta
rodearla porque la columna admite nulo desde el principio.

**Sin `server_default`**, y por eso los cuatro chatbots que ya existen nacen con nulo: heredan el
defecto de plataforma, que entra **apagado**. Una puerta nueva que puede descartar respuestas no se
enciende en producción por el hecho de existir.

Revision ID: b8u9v0w1x2y3
Revises: a7t8u9v0w1x2
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

revision = "b8u9v0w1x2y3"
down_revision = "a7t8u9v0w1x2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column("grounding_check_enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("default_grounding_check_enabled", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_organizaciones", "default_grounding_check_enabled")
    op.drop_column("hub_chatbots", "grounding_check_enabled")
