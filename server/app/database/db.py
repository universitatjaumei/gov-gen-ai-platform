"""
Server database configuration and initialization (PostgreSQL + asyncpg).
"""

import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Import models to register them with SQLModel metadata
from server.app.database import models  # noqa: F401

#: DSN de desarrollo. Es local y su credencial está publicada en el repositorio, igual que la
#: cuenta de desarrollo de `seeds.py`: no es un secreto, es un valor de conveniencia.
_DSN_DE_DESARROLLO = "postgresql+asyncpg://govgenai:govgenai_dev@localhost:5432/govgenai"


def _dsn() -> str:
    """El DSN, con el valor de desarrollo **sólo fuera de producción** (AIS.8).

    El fallback existe porque sin él no se puede arrancar en local ni correr la suite sin montar
    un `.env`, y eso es una fricción real que se paga todos los días. Lo que no puede pasar es
    que **producción** arranque con él: un despliegue al que se le olvide `DATABASE_URL` no
    fallaría, se conectaría a otra base con una credencial que cualquiera puede leer aquí, y el
    síntoma sería «faltan datos» en vez de «falta configuración».

    Es el mismo criterio con el que SEC.8.0 cerró el sembrado de la cuenta de desarrollo y con el
    que `core/config.py` rechaza el `JWT_SECRET_KEY` de ejemplo: el valor cómodo se conserva
    donde es cómodo y se prohíbe donde es peligroso.
    """
    declarado = os.environ.get("DATABASE_URL")
    if declarado:
        return declarado
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError(
            "Falta DATABASE_URL en producción. No se usa el DSN de desarrollo como reserva: "
            "arrancaría contra otra base de datos con una credencial publicada en el "
            "repositorio, y el fallo se vería como datos que faltan y no como configuración "
            "que falta."
        )
    return _DSN_DE_DESARROLLO


DATABASE_URL = _dsn()

server_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    server_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_server_db():
    """Create all tables (development only — use Alembic in production)."""
    async with server_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def seed_server_db():
    """Populates server DB with default configurations."""
    from server.app.database.models import AIConfig
    from sqlmodel import select

    async with AsyncSessionLocal() as session:
        print("[SERVER DB] Checking/Seeding AI Configs...")

        required_roles = {
            "logico_navegacion": {
                "provider": "google",
                "model_id": "gemini-3-flash-preview",
            },
            "supervision": {"provider": "google", "model_id": "gemini-3.1-pro-preview"},
            "extraccion_pdf": {
                "provider": "google",
                "model_id": "gemini-2.5-flash-lite",
            },
        }

        for role_key, default_cfg in required_roles.items():
            statement = select(AIConfig).where(AIConfig.role_key == role_key)
            results = await session.exec(statement)
            existing = results.first()

            if not existing:
                print(f"[SERVER DB] Creating role: {role_key}")
                session.add(
                    AIConfig(
                        role_key=role_key,
                        provider=default_cfg["provider"],
                        model_id=default_cfg["model_id"],
                    )
                )

        await session.commit()
        print("[SERVER DB] Seeding complete.")
