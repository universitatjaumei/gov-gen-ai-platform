"""CAL.5 — No quedan shims de compatibilidad hacia atrás en el backend.

CLAUDE.md los prohíbe explícitamente: «Sin backwards-compatibility shims. No renombres
variables a `_old_foo`, no re-exportes símbolos eliminados». Un alias como
`init_db = init_server_db` cuesta cero mantenerlo y por eso sobrevive años, pero deja dos
nombres para una cosa: quien lee `init_db` en un script no sabe si es lo mismo o algo
parecido, y el `grep` de cualquier auditoría posterior devuelve el doble de ruido.

Se comprueba sobre el árbol, no importando módulos: varios de los llamantes históricos
cuelgan de rutas anteriores al monorepo y no se pueden importar.
"""

import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[3]  # server/tests/infra/ → AI_agents_hub/

#: `_legacy_nicegui` y `_legacy_archive` estuvieron aquí hasta NIC.3/NIC.4: eran directorios
#: de código muerto que este barrido tenía que saltarse. Ya no existen, y un test de NIC.3
#: impide que vuelvan, así que la exclusión sobra.
_EXCLUIDOS = ("node_modules", ".venv", ".git")


_ESTE_FICHERO = Path(__file__).resolve()


def _ficheros_python() -> list[Path]:
    """Todo el árbol menos las cuarentenas y este mismo test.

    El test se excluye a sí mismo porque nombra el alias en sus docstrings para explicar
    qué prohíbe; sin la exclusión, el guardarraíl no puede estar nunca en verde.
    """
    return [
        p
        for p in _RAIZ.rglob("*.py")
        if p.resolve() != _ESTE_FICHERO
        and not any(parte in _EXCLUIDOS for parte in p.parts)
    ]


class TestSinShimsDeCompatibilidad:
    def test_should_import_init_server_db_directly(self):
        """`init_db` no existe: el nombre real es `init_server_db`.

        Se busca el identificador entero para no confundirlo con `init_client_db` ni con
        `scripts/init_db.py`, que es otra cosa.
        """
        patron = re.compile(r"\binit_db\b")
        culpables = []
        for fichero in _ficheros_python():
            try:
                texto = fichero.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for numero, linea in enumerate(texto.splitlines(), start=1):
                if patron.search(linea) and not linea.lstrip().startswith("#"):
                    culpables.append(f"{fichero.relative_to(_RAIZ)}:{numero}: {linea.strip()}")

        assert not culpables, (
            "Quedan referencias al alias `init_db`; el nombre real es `init_server_db`:\n  "
            + "\n  ".join(culpables)
        )

    def test_should_have_no_legacy_aliases_in_seeds(self):
        """El sembrado no arrastra identificadores de servicios que ya no existen.

        `TIER_MAPPING` asignaba tier a tres `service_id` heredados —`sys_script_gen`,
        `factory_gen` y `anchor_based`— que no los declara nadie. El bucle hace
        `session.get(...)` y sigue si no encuentra fila, así que no fallaban: simplemente no
        hacían nada, y de paso sugerían que esos servicios existían.
        """
        seeds = _RAIZ / "server" / "app" / "database" / "seeds.py"
        texto = seeds.read_text(encoding="utf-8")

        assert "Legacy alias" not in texto, (
            "`seeds.py` conserva entradas marcadas como «Legacy alias»."
        )
        for muerto in ("sys_script_gen", "factory_gen", "anchor_based"):
            assert f'"{muerto}"' not in texto, (
                f"`seeds.py` sigue asignando tier a «{muerto}», que ningún servicio declara."
            )
