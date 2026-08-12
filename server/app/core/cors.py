"""Política de CORS por entorno (SEC.3, hallazgo A4). Deploy: shared.

`allow_origins=["*"]` estaba escrito a mano en `main.py`. Con `allow_credentials=False` no
entrega cookies, así que no es el agujero de manual; lo que hace es no decidir nada, y en una
API de administración pública «no hemos decidido quién puede llamarnos» es una respuesta
mala tanto para una auditoría como para el día que aparezca un XSS en el panel.

Dos comportamientos y una razón para cada uno:

- **En producción no hay comodín**, ni escrito en la variable de entorno ni por omisión. Un
  `*` en `CORS_ALLOWED_ORIGINS` se descarta en vez de aceptarse, porque el fallo real que
  esto evita es copiar el `.env` de desarrollo a producción, no que alguien lo teclee a
  conciencia.
- **Fuera de producción el comodín se conserva.** Un desarrollador arranca el front en el
  puerto que le toca ese día, y pelearse con CORS en local no protege de nada.

**Sin lista en producción la política queda vacía y no se levanta una excepción.** CORS es
una protección del navegador: dejar el panel con un error de CORS —visible y con nombre
propio en la consola— es proporcionado; tumbar la API entera, y con ella a los clientes que
no son navegadores, no lo es.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Los que se usan. `*` haría que añadir un método nuevo no exigiera pensar si debe existir.
METODOS = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]

# `X-GovGenAI-Actor` es de SEC.2.1: sin declararla aquí, el preflight tumbaría la identidad
# delegada en cuanto un cliente delegante hablara desde un navegador.
#
# `X-Widget-Key` es de SEC.8.5: el widget público vive por definición en el origen de un
# tercero, y sin declararla el preflight responde 400 "Disallowed CORS headers" en cuanto el
# `Origin` no es el propio backend -- que es su único caso de uso real. `localhost:5173` no lo
# detecta porque Vite lo sirve por proxy y el navegador nunca ve ahí una petición cruzada.
CABECERAS = ["Authorization", "Content-Type", "Accept", "X-GovGenAI-Actor", "X-Widget-Key"]

PRODUCCION = "production"


def _origenes(csv: str | None) -> list[str]:
    return [trozo.strip() for trozo in (csv or "").split(",") if trozo.strip()]


def politica_cors(*, entorno: str, origenes_csv: str | None) -> dict:
    """Los argumentos del `CORSMiddleware` para este entorno."""
    origenes = _origenes(origenes_csv)

    if entorno == PRODUCCION:
        cerrados = [o for o in origenes if o != "*"]
        if len(cerrados) != len(origenes):
            logger.warning(
                "CORS_ALLOWED_ORIGINS incluye '*' y el entorno es producción: se descarta. "
                "Enumera los dominios del panel y de los widgets."
            )
        if not cerrados:
            logger.warning(
                "CORS_ALLOWED_ORIGINS está vacío en producción: ningún origen podrá llamar "
                "a la API desde un navegador. Configúralo con los dominios del panel."
            )
        origenes = cerrados
    elif not origenes:
        origenes = ["*"]

    return {
        "allow_origins": origenes,
        # Nunca True: el token viaja en `Authorization`, no en cookie, así que las
        # credenciales de navegador no pintan nada y activarlas solo amplía la superficie.
        "allow_credentials": False,
        "allow_methods": list(METODOS),
        "allow_headers": list(CABECERAS),
    }
