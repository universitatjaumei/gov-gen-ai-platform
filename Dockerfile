# Stage 1: Builder — instala dependencias con uv
FROM python:3.13-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# El paquete compartido debe copiarse antes de instalar server/
COPY shared/ ./shared/

# Copiar sólo los manifiestos para aprovechar caché Docker en cambios de código.
#
# `README.md` va aquí aunque no sea un manifiesto, y **quitarlo rompe la construcción entera**:
# desde PLG.1 `server/pyproject.toml` tiene `[build-system]` —sin él no hay entry points que
# descubrir— así que `uv sync` construye el wheel del proyecto, y hatchling lee `readme =
# "README.md"` y aborta con `OSError: Readme file does not exist` si no está en el contexto.
# Antes de PLG no había backend de construcción y el fichero no hacía falta.
COPY server/pyproject.toml server/uv.lock server/README.md ./server/

WORKDIR /app/server
# --no-editable convierte automatia-shared en paquete regular (no hace falta shared/ en runtime)
RUN uv sync --frozen --no-dev --no-editable


# Stage 2: Runtime — imagen mínima sin herramientas de build
FROM python:3.13-slim AS runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /app/server/.venv /app/server/.venv

# Código fuente del servidor
COPY server/app/ ./server/app/
COPY server/migrations/ ./server/migrations/
COPY server/alembic.ini ./server/alembic.ini

ENV PATH="/app/server/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# hub_themes_router crea data/themes (ruta relativa a WORKDIR) al importarse;
# /app es de root hasta aquí, así que appuser necesita este directorio ya
# creado y con permisos antes de arrancar (si no, PermissionError en el import).
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
