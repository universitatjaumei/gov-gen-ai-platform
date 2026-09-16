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
    "DECISION_MODELOS_EMBEDDING_RERANKER.md": (
        "procedencia de una medición fechada: «verificado el 2026-08-15 contra el proyecto». "
        "Generalizarla la destruye, porque el valor del dato es que se puede ir a comprobar."
    ),
}


def _documentos() -> list[Path]:
    return sorted(
        p
        for p in _DOCS.rglob("*")
        if p.suffix in {".md", ".html"} and "node_modules" not in p.parts
    )


class TestNingunDocumentoPublicaLosValoresDeEstaInstalacion:

    def test_should_not_carry_this_installations_identifiers(self):
        culpables: list[str] = []
        for doc in _documentos():
            if doc.name in _EXCEPCIONES:
                continue
            for numero, linea in enumerate(
                doc.read_text(encoding="utf-8").splitlines(), 1
            ):
                if _VALORES_DE_ESTA_CASA.search(linea):
                    culpables.append(f"{doc.name}:{numero} → {linea.strip()[:100]}")

        assert culpables == [], (
            "documentación que publica los identificadores de esta instalación:\n  "
            + "\n  ".join(culpables)
            + "\n\nSe sustituyen por marcadores. Si es la procedencia de una medición y "
            "generalizarla la destruiría, va a _EXCEPCIONES con su razón."
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
