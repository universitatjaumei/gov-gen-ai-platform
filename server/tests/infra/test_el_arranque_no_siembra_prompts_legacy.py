"""El arranque no escribe en las dos tablas de prompts del legacy (LEG.2).

`seed_all` llamaba en **cada arranque** a `seed_system_prompts`, `seed_v12_system_prompts` y
`seed_prompt_tiers`, que escriben en `extraction_service_config` y `system_prompt`. Son las líneas
`[SEED] Iniciando poblado de SystemPrompt…` del log de desarrollo.

Escribir en la base de datos al arrancar es lo que **choca con la suite**: el servidor siembra
mientras los tests reinicializan, y salta cualquiera de los dos. De ahí los dos síntomas ya
observados con una sola causa: arranques fallidos en desarrollo y `tests/test_prompts.py` inestable
—pasa aislado y falla en la suite paralela—.

Las tablas son huérfanas: su único consumidor (`knowledge_orchestrator_service.py`) no lo importa
nadie. Los prompts vivos son `HubPromptTemplate` y `HubActivityPrompt`, que este bloque no toca.
"""
from __future__ import annotations

import inspect
from pathlib import Path


def _fuente_de_seeds() -> str:
    from server.app.database import seeds

    return inspect.getsource(seeds)


def test_el_arranque_no_llama_a_la_siembra_de_prompts():
    fuente = _fuente_de_seeds()

    for funcion in ("seed_system_prompts", "seed_v12_system_prompts", "seed_prompt_tiers"):
        assert funcion not in fuente, (
            f"`{funcion}` sigue en seeds.py: el arranque escribe en las tablas legacy y "
            f"colisiona con la suite"
        )


def test_el_modulo_de_siembra_de_prompts_ya_no_existe():
    raiz = Path(__file__).resolve().parents[2]

    assert not (raiz / "app" / "database" / "seeds_prompts.py").exists()


def test_nadie_importa_el_modulo_de_siembra_de_prompts():
    """El `grep -r` a cero que exige CLAUDE.md, como test para que no vuelva."""
    raiz = Path(__file__).resolve().parents[2]
    culpables: list[str] = []

    # Sólo el código del proyecto: `rglob` desde la raíz recorrería `.venv` entero.
    for carpeta in ("app", "tests", "migrations"):
        for fichero in (raiz / carpeta).rglob("*.py"):
            if "_legacy" in str(fichero) or "__pycache__" in str(fichero):
                continue
            if fichero.name == Path(__file__).name:
                continue
            if "seeds_prompts" in fichero.read_text(encoding="utf-8", errors="ignore"):
                culpables.append(str(fichero.relative_to(raiz)))

    assert culpables == [], f"quedan referencias a seeds_prompts: {culpables}"


def test_el_arranque_conserva_lo_que_si_hace_falta():
    """El arranque hace más cosas, y retirar la siembra no puede llevarse ninguna."""
    fuente = _fuente_de_seeds()

    assert "seed_server_db" in fuente
    assert "seed_multitenancy_defaults" in fuente


def test_las_dos_clases_legacy_no_se_usan_en_los_seeds():
    fuente = _fuente_de_seeds()

    assert "ExtractionServiceConfig" not in fuente
    assert "SystemPrompt" not in fuente
