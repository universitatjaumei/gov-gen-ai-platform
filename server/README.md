# `automatia-server` — el servidor de Gov Gen AI Platform

API FastAPI de la plataforma: asistentes RAG y agénticos, ingesta del corpus, redacción de
informes, curación de portales y la superficie administrativa.

La documentación vive en [`../docs/`](../docs/); el mapa de módulos y las reglas de contribución,
en [`../AGENTS.md`](../AGENTS.md).

## Arrancar en local

```bash
uv sync --locked                 # o --all-extras, que es lo que usa CI
uv run alembic upgrade head      # el esquema lo define Alembic, y sólo Alembic
cd .. && uv run --project server uvicorn server.app.main:app --port 8000
```

El servidor se arranca **desde la raíz del repositorio**, no desde aquí: el paquete importable es
`server.app`, así que la raíz tiene que estar en `sys.path`.

## Tests

```bash
uv run pytest tests              # desde Git Bash, no desde PowerShell
```

`tests/infra/test_setup_script.py` invoca `bash`, que en PowerShell resuelve al lanzador de WSL y
da falsos rojos. CI corre con `-n0` a propósito: el paralelismo esconde el estado filtrado entre
tests.
