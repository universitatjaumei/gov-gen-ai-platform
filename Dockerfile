# Stage 1: Builder — instala dependencias con uv
FROM python:3.11-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# El paquete compartido debe copiarse antes de instalar server/
COPY shared/ ./shared/

# Copiar sólo los manifiestos para aprovechar caché Docker en cambios de código
COPY server/pyproject.toml server/uv.lock ./server/

WORKDIR /app/server
# --no-editable convierte automatia-shared en paquete regular (no hace falta shared/ en runtime)
RUN uv sync --frozen --no-dev --no-editable


# Stage 2: Runtime — imagen mínima sin herramientas de build
FROM python:3.11-slim AS runtime

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

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
