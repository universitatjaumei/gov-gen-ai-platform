# Stage 1: Builder — instala dependencias con uv
FROM python:3.14-slim AS builder

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
FROM python:3.14-slim AS runtime

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

# APER.3 — el entorno se ancla aquí, y no se deja al valor por omisión del código.
#
# `core/config.py` y `database/seeds.py` leen los dos `os.getenv("ENVIRONMENT", "development")`,
# o sea que **un ENVIRONMENT ausente significa «sin protecciones»**: no corre ninguno de los
# cuatro gates de producción y se siembra `admin@example.local` con una contraseña escrita en el
# propio repositorio. Los dos composes y el job `imagen` de CI lo fijan, así que el despliegue de
# la UJI nunca estuvo afectado; el riesgo es de quien despliegue desde el repositorio público con
# un `docker run` y sólo `JWT_SECRET_KEY`.
#
# Se ancla en la imagen y no dándole la vuelta al defecto del código porque en el host —la
# suite, el desarrollo— `TESTING=1` y `SANDBOX_MODE=local` son correctos, y los gates los
# rechazan: invertirlo rompería todo eso para arreglar un caso que sólo ocurre aquí. Quien
# necesite la imagen en modo desarrollo lo sobrescribe al arrancarla, que es un acto explícito.
ENV ENVIRONMENT=production

# hub_themes_router crea data/themes (ruta relativa a WORKDIR) al importarse;
# /app es de root hasta aquí, así que appuser necesita este directorio ya
# creado y con permisos antes de arrancar (si no, PermissionError en el import).
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
