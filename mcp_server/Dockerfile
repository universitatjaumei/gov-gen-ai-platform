# Imagen del MCP remoto (REG.4).
#
# Proceso pequeño y sin estado: habla HTTP con la API y nada más. No lleva el venv del servidor
# ni cliente de base de datos, porque el paquete no importa `server.app` —hay un test que lo
# comprueba— y eso es lo que le permite ser esta imagen y no la del servidor entera.
#
# El transporte y el modelo de autenticación están en `http_server.py`: streamable HTTP, sin
# sesión, y el PAT lo presenta cada cliente en su petición. Aquí no se configura ningún token.
FROM python:3.14-slim

WORKDIR /srv/mcp

COPY pyproject.toml uv.lock ./
# `--frozen` y no `--locked`: el lock manda y no se vuelve a resolver. Sin esto, una imagen
# construida meses después podría traer versiones que nadie probó.
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY config.py api_client.py errors.py resources.py server.py http_server.py ./
COPY tools/ ./tools/

# El venv ya está sincronizado, así que uvicorn se invoca directamente desde él y nunca por
# `uv run`: `uv run` vuelve a resolver el proyecto en cada arranque, lo que necesita red y un
# $HOME escribible — mismo motivo que en el Dockerfile de la raíz y en el del sandbox.
ENV PATH="/srv/mcp/.venv/bin:$PATH"

# Sin usuario propio ni ficheros que escribir: nada aquí necesita root.
USER 65534:65534
EXPOSE 8080

# `--factory` porque `app` es una función: la aplicación se construye al arrancar, cuando las
# variables de entorno ya están, y no al importar el módulo.
CMD ["uvicorn", "http_server:app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
