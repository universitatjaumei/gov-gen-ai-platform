"""La documentación de AutomatIA no describe esta aplicación, y no puede volver a `docs/`.

`docs/` arrastraba diecisiete ficheros que no estaban desfasados: describían **otro producto**
—el *Client Node*, el *Brain*, su `brain_server.db`, «AutomatIA V4.0»—, y su índice
(`docs/README.md`) era el índice de aquel producto. Formaban una isla cerrada: sólo se
referenciaban entre ellos, y ni el plan, ni el código, ni CI, ni el `README` apuntaban ahí.

El daño no era de cara a la publicación, era del día a día: quien —persona o agente— abría
`docs/technical/architecture_detailed.md` se llevaba una arquitectura que no es la de este
proyecto, y la que sí lo es está en `docs/Arquitectura.md`, al lado.

**Estuvieron en cuarentena hasta el 2026-09-04, y ese día se retiraron con ella.** La cuarentena
existía para que el Bloque NIC pudiera inventariar qué de `client_app/` estaba cubierto, y estos
diecisiete eran la descripción de lo que había. Hecho el inventario
—`docs/INVENTARIO_RETIRADA_LEGACY.md`, que es lo que sobrevive—, se fueron con el resto del
NiceGUI: se leen en el historial de git.

**De este guardarraíl murió un test y sobrevivieron tres, y la asimetría es la que importa.** El
que afirmaba «los diecisiete siguen en la cuarentena» se quedó sin sujeto. Los otros tres no
dependen de que existan en ningún sitio, y son los que evitan el daño real del día a día: que
ninguno **vuelva** a `docs/`, que `docs/functional/` y `docs/technical/` no reaparezcan vacíos
invitando a rellenarlos, y que ningún fichero activo los enlace. Ese daño no era de cara a la
publicación: era que quien abría `docs/technical/architecture_detailed.md` se llevaba la
arquitectura de otro producto, con la de este al lado.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
CUARENTENA = RAIZ / "_legacy_nicegui" / "docs"

#: Los diecisiete, con la ruta que tenían dentro de `docs/`.
DOCUMENTOS_DE_AUTOMATIA = (
    "ETL_USER_GUIDE.md",
    "INTERNAL_API.md",
    "MANUAL_ADMIN.md",
    "deployment_guide.md",
    "network_status_widget.md",
    "quick_start.md",
    "troubleshooting.md",
    "functional/flows_configuration.md",
    "functional/partner_admin_guide.md",
    "functional/user_manual_client.md",
    "technical/api_reference.md",
    "technical/architecture_detailed.md",
    "technical/database_schema.md",
    "technical/factory_modules.md",
    "technical/new_features_v4.md",
    "technical/runtime_engine.md",
    "technical/security_model.md",
)

#: Dónde se busca una referencia viva. `planificacion/` queda fuera a propósito: su historial
#: cuenta lo que se hizo, y citar un fichero movido es correcto ahí.
ARBOLES_ACTIVOS = ("server/app", "frontend/src", "docs", "scripts", ".github", "mcp_server")

IGNORADOS = {".venv", "node_modules", "generated", "__pycache__", "_legacy_nicegui"}


def _ficheros_activos():
    for arbol in ARBOLES_ACTIVOS:
        base = RAIZ / arbol
        if not base.exists():
            continue
        for ruta in base.rglob("*"):
            if not ruta.is_file():
                continue
            if IGNORADOS & set(ruta.relative_to(RAIZ).parts):
                continue
            if ruta.suffix.lower() in (".md", ".py", ".ts", ".tsx", ".yml", ".yaml", ".html"):
                yield ruta


class TestLaIslaSigueEnCuarentena:

    @pytest.mark.parametrize("relativa", DOCUMENTOS_DE_AUTOMATIA)
    def test_should_keep_each_automatia_doc_out_of_docs(self, relativa: str):
        assert not (RAIZ / "docs" / relativa).exists(), (
            f"docs/{relativa} describe AutomatIA, no esta plataforma. Se retiró el 2026-09-04; "
            "si hace falta consultarlo, está en el historial de git."
        )

    def test_should_have_no_quarantine_left_to_check(self):
        """Aquí se afirmaba que los diecisiete seguían en `_legacy_nicegui/docs/`.

        NIC.3 retiró la cuarentena, así que la afirmación es falsa **por diseño**, no por
        descuido, y se sustituye por la contraria. La distinción no es retórica: un test que
        comprueba la presencia de ficheros en un directorio borrado no se puede «arreglar»
        volviendo a crearlos.
        """
        assert not CUARENTENA.exists(), (
            "_legacy_nicegui/docs/ volvió al árbol. La referencia es el historial de git, "
            "no un directorio de documentación de otro producto dentro del repositorio"
        )

    def test_should_not_leave_the_emptied_directories_behind(self):
        for vacio in ("functional", "technical"):
            assert not (RAIZ / "docs" / vacio).exists(), (
                f"docs/{vacio}/ quedó vacío al mover la isla: un directorio vacío invita a "
                "volver a llenarlo."
            )


class TestNadaActivoLaReferencia:

    def test_should_not_be_linked_from_any_active_file(self):
        """El índice viejo enlazaba los diecisiete. El nuevo no puede volver a hacerlo.

        Se buscan los nombres de fichero, no rutas completas, porque un enlace relativo desde
        `docs/` se escribe `quick_start.md` sin prefijo.
        """
        nombres = {Path(r).name for r in DOCUMENTOS_DE_AUTOMATIA}
        # `README.md` no: es un nombre demasiado común. Ninguno de los diecisiete se llama así.
        patron = re.compile("|".join(re.escape(n) for n in nombres))

        culpables = []
        for ruta in _ficheros_activos():
            texto = ruta.read_text(encoding="utf-8", errors="ignore")
            for encontrado in patron.finditer(texto):
                linea = texto[: encontrado.start()].count("\n") + 1
                culpables.append(f"{ruta.relative_to(RAIZ)}:{linea} → {encontrado.group()}")

        assert culpables == [], (
            "estos ficheros activos referencian documentación de AutomatIA que está en "
            "cuarentena, así que el enlace está roto:\n  " + "\n  ".join(culpables)
        )
