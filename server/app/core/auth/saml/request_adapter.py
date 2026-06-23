"""Adapta el ``Request`` de FastAPI al dict que espera python3-saml."""

from typing import Any


async def prepare_saml_request(request: Any) -> dict:
    """Convierte un ``Request`` (Starlette/FastAPI) al formato de OneLogin.

    OneLogin reconstruye la URL actual a partir de ``https``/``http_host``/``script_name``
    para validar el ``Destination`` y el ``Recipient`` de la aserción.
    """
    post_data: dict = {}
    if request.method == "POST":
        form = await request.form()
        post_data = {key: form[key] for key in form}

    url = request.url
    host = url.hostname or request.headers.get("host", "")

    req: dict = {
        "https": "on" if url.scheme == "https" else "off",
        "http_host": host,
        "script_name": url.path,
        "get_data": dict(request.query_params),
        "post_data": post_data,
    }
    if url.port:
        req["server_port"] = str(url.port)
    return req
