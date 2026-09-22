"""REPO.5 — la documentación publica el procedimiento, no los valores de esta instalación.

El repositorio se va a abrir, y `docs/` llevaba los identificadores de **esta** instalación:
el proyecto de GCP, la instancia de Cloud SQL, la máquina, los *buckets* y el host provisional.
No son credenciales —lo que protege el acceso es IAM, no que el nombre sea secreto— así que esto
no va de secretos. Va de dos cosas concretas:

1. **Utilidad.** El procedimiento de `DESPLIEGUE_PROTOTIPO_GCP.md` es de lo más valioso que se
   puede publicar, porque es justo lo que una entidad local no sabe hacer. Con los valores de
   esta casa dentro **no sirve**: quien lo siga tiene que adivinar qué sustituir.
2. **No repartir el inventario de qué sondear.** Publicar proyecto, instancia, VM y *buckets*
   junto no añade nada al lector y sí le ahorra trabajo a quien busque una superficie.

Es exactamente lo que el código ya resolvió y la documentación nunca recibió: los identificadores
viven en variables, no escritos dentro. `deploy.yml` no lleva ninguno.

**La distinción que gobierna la lista de excepciones**, y es la misma que usa
`test_ais2_nada_institucional_en_el_principal.py` entre código y comentario:

* Un **valor de instrucción o de ejemplo copiable** —una celda de la tabla de variables, un
  `data-api-url=` que alguien va a pegar— se sustituye por un marcador. Quien copie el ejemplo de
  `WIDGET_INCRUSTACION.md` estaría apuntando su widget **a nuestra API**.
* Una **procedencia de medición** —«verificado el 2026-08-15 contra el proyecto `uji-teclab`»— se
  **conserva**: generalizarla la destruye, porque «verificado contra `<PROYECTO>`» no dice nada y
  el valor del dato está en que se puede ir a comprobar.

Por eso hay excepciones y no una prohibición total. Cada una lleva su razón, que es para lo que
la lista existe.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_DOCS = Path("../docs")

#: `planificacion/` entró aquí el 2026-09-22, al preparar la apertura. El guardarraíl vivía
#: mirando sólo `docs/`, y ahí estaba el hueco: de las 25 apariciones de los identificadores de
#: esta casa, **quince estaban en `planificacion/`**, que nadie miraba. Es el patrón de siempre —se
#: cumple donde está mecanizado y se escapa donde sólo estaba escrito— y por eso la respuesta no
#: fue un barrido a mano sino ampliar el alcance: un barrido se hace una vez, esto se comprueba en
#: cada ejecución.
_PLANIFICACION = Path("../planificacion")

#: Los identificadores de ESTA instalación. No incluye `normativa.uji.es` —el dominio público del
#: servicio, que es público por definición y aparece en las citas del propio corpus— ni la región
#: `europe-southwest1`, que es un dato de GCP y no una identidad: un documento que diga «Madrid»
#: es más útil que uno que diga `<REGION>`.
#:
#: **La IP va en las DOS formas, y ésa fue la avería.** Hasta el 2026-09-16 este patrón sólo
#: llevaba `34-175-38-129`, con guiones, que era como se escribía dentro del host provisional de
#: entonces. La IP de verdad se escribe con puntos, así que el guardarraíl pasó **nueve días en
#: verde con la IP de producción dentro de `DESPLIEGUE_PROTOTIPO_GCP.md`**. No lo encontró el
#: test: lo encontró un barrido a mano del contenido, al preparar la apertura del repositorio.
#: Un guardarraíl que no mira nada pasa en verde igual que uno que mira y no encuentra nada.
_VALORES_DE_ESTA_CASA = re.compile(
    r"(uji-teclab|govgenai-prod|govgenai-vm|govgenai-normativa-uji"
    r"|34-175-38-129|34\.175\.38\.129|618806480921)"
)

#: (fichero, línea, razón). Procedencias de medición: el valor está en poder ir a comprobarlo.
_EXCEPCIONES: dict[str, str] = {
    "docs/DECISION_MODELOS_EMBEDDING_RERANKER.md": (
        "procedencia de una medición fechada: «verificado el 2026-08-15 contra el proyecto». "
        "Generalizarla la destruye, porque el valor del dato es que se puede ir a comprobar."
    ),
    # --- `planificacion/`, clasificadas el 2026-09-22 con el mismo criterio de arriba ---
    "planificacion/HISTORIAL.md": (
        "es el registro, y su contenido **es** procedencia por definición: una fila por prompt "
        "cerrado, con qué se midió y contra qué. Sustituir ahí los valores no protege nada —el "
        "fichero no se copia, se lee— y destruye lo único que hace útil una fila vieja."
    ),
    "planificacion/PROJECT_STATE.md": (
        "el cursor y el estado de los bloques. Misma razón que el historial: lo que aparece son "
        "narraciones de lo medido («ya estaba habilitado en el proyecto»), no valores copiables."
    ),
    "fase1/50_BLOQUE_PIL.md": (
        "«Prerrequisitos externos resueltos el 2026-08-15» y «Medido contra la API real "
        "(2026-08-15, proyecto ...)». Es la procedencia de la medición que fija PIL.1."
    ),
    "fase1/68_BLOQUE_DOM.md": (
        "narración de lo que se midió del DNS y del certificado: que la VM responde en esa IP y "
        "el bucket en siete rotando es el hallazgo, y sin las cifras no queda hallazgo."
    ),
    "fase1/61_BLOQUE_REPO.md": (
        "los mandatos copiables ya llevan marcadores (sustituidos el 2026-09-22); lo que queda "
        "es la narración del fallo de ESTE guardarraíl —buscaba la IP con guiones y el documento "
        "la escribía con puntos, y pasó nueve días en verde—. Escribir ahí un marcador borra "
        "justo el detalle que explica el fallo."
    ),
    "fase1/52_BLOQUE_PRO.md": (
        "falso positivo: `govgenai-prod-script-sandbox` es el nombre de una imagen Docker local "
        "que contiene la cadena, no la instancia de producción. El patrón busca subcadenas y "
        "aquí acierta en la letra y falla en el sentido."
    ),
}


def _documentos() -> list[Path]:
    return sorted(
        p
        for raiz in (_DOCS, _PLANIFICACION)
        for p in raiz.rglob("*")
        if p.suffix in {".md", ".html"} and "node_modules" not in p.parts
    )


def _clave(doc: Path) -> str:
    """`carpeta/fichero`, y no sólo el nombre.

    Con dos árboles, un `README.md` de cada uno compartiría clave y una exención escrita para
    uno eximiría al otro en silencio. Es el mismo fallo que la lista existe para evitar.
    """
    return f"{doc.parent.name}/{doc.name}"


class TestNingunDocumentoPublicaLosValoresDeEstaInstalacion:

    def test_should_not_carry_this_installations_identifiers(self):
        culpables: list[str] = []
        for doc in _documentos():
            if _clave(doc) in _EXCEPCIONES:
                continue
            for numero, linea in enumerate(
                doc.read_text(encoding="utf-8").splitlines(), 1
            ):
                if _VALORES_DE_ESTA_CASA.search(linea):
                    culpables.append(f"{_clave(doc)}:{numero} → {linea.strip()[:100]}")

        assert culpables == [], (
            "documentación que publica los identificadores de esta instalación:\n  "
            + "\n  ".join(culpables)
            + "\n\nSe sustituyen por marcadores. Si es la procedencia de una medición y "
            "generalizarla la destruiría, va a _EXCEPCIONES con su razón."
        )


#: Qué cuenta como **copiable**: un mandato de consola o una asignación de variable.
#:
#: La primera versión de esto decía «lo que esté dentro de una valla ```» y **estaba mal**, con
#: cinco falsos positivos. En `planificacion/` los prompts se escriben enteros dentro de vallas
#: —prosa, encabezados y tablas incluidos—, así que la valla no separa lo copiable de lo narrado;
#: ahí dentro hay tanto `gcloud sql instances create` como «## Medido contra la API real».
#:
#: Mirar la forma de la línea sí los separa, y además funciona igual en los dos árboles.
_ES_COPIABLE = re.compile(
    r"^\s*(?:\$\s*)?(?:sudo\s+)?(?:gcloud|gsutil|gh|docker|kubectl|psql|curl|terraform)\s"
    r"|^\s*[A-Z][A-Z0-9_]*="
    r"|--(?:project|instance|set-env-vars|add-cloudsql-instances|workload-identity-pool)="
)


def _lineas_copiables(texto: str) -> list[tuple[int, str]]:
    return [
        (numero, linea)
        for numero, linea in enumerate(texto.splitlines(), 1)
        if _ES_COPIABLE.search(linea)
    ]


class TestLasExencionesSiguenSiendoHonestas:
    """Una exención de fichero entero deja ese fichero ciego, y eso hay que acotarlo.

    La distinción que gobierna la lista es **prosa contra mandato**: una procedencia de medición
    se conserva porque nadie la copia, se lee. Un bloque de código sí se copia, y ahí el valor no
    tiene defensa posible — da igual en qué fichero esté.

    Así que la exención cubre la prosa y **nunca** un bloque cercado. Sin esto, exonerar un
    fichero por su narrativa exoneraría de paso cualquier mandato que se le añada después, que es
    exactamente la forma en que una lista de excepciones se convierte en un agujero.
    """

    def test_ningun_fichero_eximido_lleva_los_valores_en_una_linea_copiable(self):
        culpables: list[str] = []
        for doc in _documentos():
            if _clave(doc) not in _EXCEPCIONES:
                continue
            for numero, linea in _lineas_copiables(doc.read_text(encoding="utf-8")):
                if _VALORES_DE_ESTA_CASA.search(linea):
                    culpables.append(f"{_clave(doc)}:{numero} → {linea.strip()[:100]}")

        assert culpables == [], (
            "ficheros eximidos que llevan los valores de esta instalación en una línea "
            "**copiable** (un mandato o una asignación):\n  "
            + "\n  ".join(culpables)
            + "\n\nLa exención cubre la prosa, no los mandatos. Sustitúyelos por marcadores."
        )

    def test_ninguna_exencion_sobra(self):
        """Una exención que ya no corresponde a nada es ruido que confunde al siguiente."""
        con_valores = {
            _clave(doc)
            for doc in _documentos()
            if _VALORES_DE_ESTA_CASA.search(doc.read_text(encoding="utf-8"))
        }
        sobran = sorted(set(_EXCEPCIONES) - con_valores)
        assert sobran == [], (
            f"estas exenciones ya no corresponden a ningún fichero con valores: {sobran}. "
            "Si el valor desapareció, la exención se quita."
        )


class TestElDespliegueSeDocumentaCompleto:
    """Tres datos de `DESPLIEGUE_PROTOTIPO_GCP.md` que habían dejado de ser ciertos.

    Un documento de despliegue que miente en las cifras es peor que no tenerlo: quien lo siga
    creerá que ha terminado cuando le falta algo. Los tres se encontraron al preparar REPO.5.
    """

    @pytest.fixture
    def texto(self) -> str:
        return (_DOCS / "DESPLIEGUE_PROTOTIPO_GCP.md").read_text(encoding="utf-8")

    def test_should_document_both_anchors_of_the_federated_identity(self, texto: str):
        """El nombre del repositorio está anclado en DOS sitios, no en uno.

        Medido el 2026-09-07: la condición del proveedor **y** el `principalSet` del enlace de
        la cuenta de servicio. Quien siga el documento con uno solo se queda a medias, y el
        síntoma —la autenticación falla— no señala a lo que falta.
        """
        assert "assertion.repository" in texto, "falta la condición del proveedor"
        assert "principalSet" in texto, (
            "falta el segundo anclaje: el `principalSet` del enlace de la cuenta de servicio. "
            "El nombre del repositorio está en DOS sitios y el documento sólo nombra uno"
        )

    def test_should_count_four_images(self, texto: str):
        """`deploy.yml` construye cuatro: app, frontend, sandbox y **mcp** desde REG.4."""
        assert "Tres imágenes" not in texto, (
            "sigue diciendo «Tres imágenes»: son cuatro desde REG.4, que añadió `mcp`"
        )

    def test_should_count_twelve_repository_variables(self, texto: str):
        """Medidas el 2026-09-07 con `gh variable list`: doce."""
        assert not re.search(
            r"\bDiez\b.*variables|variables.*\bDiez\b", texto, re.IGNORECASE
        ), (
            "sigue diciendo «Diez» variables: son doce, medidas con `gh variable list`"
        )
