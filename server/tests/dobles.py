"""Dobles de chatbot que no hay que retocar cada vez que se añade una columna.

**El problema que resuelve.** Los tests del chat doblan el chatbot con
`MagicMock(spec=HubChatbot)`, y un `MagicMock` inventa un valor para **cualquier** atributo
que no se le haya declarado. Mientras el endpoint solo leía `id` y `retrieval_mode` eso no
molestaba; desde que las guardas miran el modo de acceso (SEC.2.1), las cuotas (SEC.4) y la
ventana de vigencia (SEC.4.1), cada columna nueva convierte a los dobles en un chatbot con
valores absurdos —un `access_mode` que no existe, un límite de un token, una fecha que es un
mock— y cinco ficheros de tests se ponen en rojo por algo que no es el cambio que se estaba
probando.

Ha pasado tres veces seguidas. La cuarta se evita aquí: en vez de enumerar a mano los
campos, se leen del ORM y se rellena **solo lo que el test no haya declarado**, con el
mismo valor por defecto que tendría una fila recién creada.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from server.app.modules.agents_hub.database.config_models import HubChatbot


def _valor_por_defecto(columna):
    """El default declarado en el ORM, o `None` si no hay ninguno.

    Los `default` que son invocables —`uuid4`, `list`, la hora actual— se llaman; los
    escalares se copian tal cual. Un `server_default` no se mira: eso lo pone Postgres y
    aquí no hay Postgres.
    """
    defecto = columna.default
    if defecto is None:
        return None
    argumento = getattr(defecto, "arg", None)
    if callable(argumento):
        try:
            return argumento(None)
        except TypeError:
            return argumento()
    return argumento


def completar_chatbot(doble, **declarados):
    """Rellena el doble con los defaults del ORM y devuelve el propio doble.

    Lo que el test ya haya puesto se respeta: solo se tocan los atributos que siguen siendo
    un `MagicMock`, que es la señal de «esto no lo ha declarado nadie».
    """
    for nombre, valor in declarados.items():
        setattr(doble, nombre, valor)

    for columna in HubChatbot.__table__.columns:
        actual = getattr(doble, columna.name, None)
        if isinstance(actual, MagicMock):
            setattr(doble, columna.name, _valor_por_defecto(columna))

    return doble
