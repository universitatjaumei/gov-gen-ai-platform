FROM python:3.14-slim

# Dependencias del sistema mínimas (libgomp1 lo necesita numpy/pandas en algunos entornos).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root con UID 65534 (nobody). El `|| true` cubre el caso de que la
# distribución base ya tenga ese UID asignado a otro usuario.
RUN useradd --uid 65534 --no-create-home --shell /usr/sbin/nologin sandboxuser \
    || true

WORKDIR /srv/sandbox

COPY pyproject.toml ./
COPY uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev || \
    (pip install --no-cache-dir uv && uv sync --no-dev)

COPY sandbox/ ./sandbox/

# /tmp/sandbox lo monta el orquestador (SBX.4) como tmpfs; aquí solo lo
# creamos por si el contenedor se ejecuta sin el tmpfs en local.
RUN mkdir -p /tmp/sandbox && chown 65534:65534 /tmp/sandbox

# El venv ya quedó sincronizado por `uv sync` en el paso anterior (con red
# disponible en build-time). El CMD debe invocar uvicorn DIRECTAMENTE desde
# ese venv, nunca vía `uv run`: `uv run` re-resuelve/reconstruye el proyecto
# local en cada arranque (necesita red para el build backend), y este
# contenedor corre sin red (sandbox-net internal) y sin $HOME escribible
# (USER 65534, root fs read_only) — mismo patrón que el Dockerfile raíz.
ENV PATH="/srv/sandbox/.venv/bin:$PATH"

USER 65534:65534
EXPOSE 5000

CMD ["uvicorn", "sandbox.main:app", "--host", "0.0.0.0", "--port", "5000"]
