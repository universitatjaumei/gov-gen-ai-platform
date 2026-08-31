"""El despliegue: sin claves de larga vida, con etiqueta identificable y con vuelta atrás (D.5-VM).

Los tres invariantes que este workflow tiene que cumplir, y que se rompen sin ruido:

- **Ninguna credencial permanente.** Una clave JSON de cuenta de servicio en los secretos del
  repositorio es una credencial que nadie rota y que se lleva quien lea los secretos una vez.
  Se autentica por federación, y aquí se comprueba que no ha vuelto una clave.
- **La etiqueta es el SHA, nunca `latest`.** Con `latest` no se puede responder «qué está
  corriendo» ni «vuelve a lo de antes», que son las dos preguntas de un incidente.
- **Las migraciones van antes de cambiar la imagen.** El orden es el invariante, no la
  existencia del paso: si se cuelan después, un fallo de Alembic deja la imagen nueva sirviendo
  contra un esquema viejo.

Y una cuarta que es del aprovisionamiento: el proveedor de identidad tiene que estar **acotado
al repositorio**. Sin `--attribute-condition`, acepta tokens de cualquier repositorio de GitHub
y cualquiera podría suplantar a la cuenta de despliegue. Es el error clásico de esta
configuración.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
WORKFLOW = RAIZ / ".github" / "workflows" / "deploy.yml"
PROVISION = RAIZ / "scripts" / "gcp_provision_cicd.sh"
COMPOSE = RAIZ / "deploy" / "vm" / "docker-compose.vm.yml"


def _texto(ruta: Path) -> str:
    assert ruta.is_file(), f"Falta {ruta.relative_to(RAIZ).as_posix()}"
    return ruta.read_text(encoding="utf-8")


def _workflow() -> dict:
    return yaml.safe_load(_texto(WORKFLOW))


def _pasos() -> list[dict]:
    datos = _workflow()
    trabajos = datos["jobs"]
    assert len(trabajos) == 1, "Se espera un solo trabajo de despliegue."
    return next(iter(trabajos.values()))["steps"]


def _nombres_de_paso() -> list[str]:
    return [p.get("name", p.get("uses", "")) for p in _pasos()]


def test_el_workflow_es_yaml_valido_y_tiene_un_solo_trabajo() -> None:
    datos = _workflow()
    assert "jobs" in datos
    assert datos.get("concurrency", {}).get("cancel-in-progress") is False, (
        "Un despliegue a medias no se cancela: dejaría la máquina en un estado intermedio."
    )


# ---------------------------------------------------------------------------
# Sin claves de larga vida
# ---------------------------------------------------------------------------


def test_se_autentica_por_federacion_y_no_con_una_clave() -> None:
    texto = _texto(WORKFLOW)
    assert "workload_identity_provider" in texto, "Falta la federación de identidad."
    assert "credentials_json" not in texto, (
        "`credentials_json` es una clave de cuenta de servicio: una credencial permanente en "
        "los secretos del repositorio. Se autentica por federación."
    )
    assert not re.search(r"secrets\.GCP_[A-Z_]*KEY", texto), (
        "No debe haber ninguna clave de GCP en los secretos del repositorio."
    )

    datos = _workflow()
    assert datos["permissions"]["id-token"] == "write", (
        "La federación exige `id-token: write`; sin ello el canje de token falla."
    )


def test_los_identificadores_van_en_vars_y_no_en_secrets() -> None:
    """Un proyecto o una región no son secretos, y tratarlos como tales esconde qué se
    despliega a dónde sin proteger nada."""
    texto = _texto(WORKFLOW)
    for identificador in ("GCP_PROJECT_ID", "GCP_REGION", "GCP_WIF_PROVIDER", "GCP_DEPLOY_SA"):
        assert f"vars.{identificador}" in texto, f"{identificador} debería venir de `vars`"
        assert f"secrets.{identificador}" not in texto


# ---------------------------------------------------------------------------
# La etiqueta
# ---------------------------------------------------------------------------


def test_la_imagen_se_etiqueta_con_el_sha_y_nunca_con_latest() -> None:
    texto = _texto(WORKFLOW)
    assert "GITHUB_SHA" in texto, "La etiqueta tiene que salir del SHA del commit."
    etiquetas_latest = re.findall(r":latest\b", texto)
    assert not etiquetas_latest, (
        "`latest` no sirve para saber qué corre ni para volver atrás: usa el SHA."
    )


def test_se_puede_desplegar_una_etiqueta_concreta_para_volver_atras() -> None:
    datos = _workflow()
    # `on:` lo parsea YAML 1.1 como el booleano True, no como la cadena "on". Es la trampa
    # clásica de leer un workflow de GitHub con `yaml.safe_load`, y cayó el primer intento.
    disparadores = datos.get("on", datos.get(True))
    assert disparadores, "No se han podido leer los disparadores del workflow."
    entradas = disparadores["workflow_dispatch"]["inputs"]
    assert "etiqueta" in entradas, (
        "Tiene que poder lanzarse a mano con una etiqueta: es el camino de vuelta manual."
    )


# ---------------------------------------------------------------------------
# El orden, que es el invariante
# ---------------------------------------------------------------------------


def test_las_migraciones_van_antes_de_cambiar_la_imagen() -> None:
    nombres = _nombres_de_paso()
    indice_migracion = next(
        (i for i, n in enumerate(nombres) if "Migraciones" in n), None
    )
    indice_despliegue = next(
        (i for i, n in enumerate(nombres) if n.strip() == "Desplegar"), None
    )
    assert indice_migracion is not None, f"No hay paso de migraciones: {nombres}"
    assert indice_despliegue is not None, f"No hay paso de despliegue: {nombres}"
    assert indice_migracion < indice_despliegue, (
        "Las migraciones tienen que ir ANTES de cambiar la imagen. Si van después, un fallo "
        "de Alembic deja la imagen nueva sirviendo contra un esquema viejo."
    )


def test_el_cliente_de_la_api_se_genera_antes_de_construir_las_imagenes() -> None:
    """`frontend/src/shared/api/generated/` está en .gitignore: es código generado por Orval
    desde `openapi.json` y no viaja en el repositorio. Sin generarlo, `docker build ./frontend`
    falla con veinte «Cannot find module '@/shared/api/generated/…'» — que es exactamente
    dónde murió el primer despliegue.
    """
    nombres = _nombres_de_paso()
    indice_cliente = next(
        (i for i, n in enumerate(nombres) if "cliente de la API" in n), None
    )
    indice_imagenes = next(
        (i for i, n in enumerate(nombres) if "imágenes" in n or "imagenes" in n), None
    )
    assert indice_cliente is not None, (
        f"Falta el paso que genera el cliente de la API: {nombres}"
    )
    assert indice_imagenes is not None, f"Falta el paso que construye las imágenes: {nombres}"
    assert indice_cliente < indice_imagenes, (
        "El cliente se genera ANTES de construir la imagen del frontend."
    )

    texto = _texto(WORKFLOW)
    assert "export_openapi.py" in texto, (
        "El cliente sale de `openapi.json`, que exporta el backend: sin ese paso, Orval "
        "generaría contra un contrato viejo o ninguno."
    )
    assert "generate:api" in texto


def test_la_etiqueta_anterior_se_guarda_antes_de_desplegar() -> None:
    nombres = _nombres_de_paso()
    indice_anterior = next((i for i, n in enumerate(nombres) if "anterior" in n), None)
    indice_despliegue = next((i for i, n in enumerate(nombres) if n.strip() == "Desplegar"), None)
    assert indice_anterior is not None, "No se guarda la etiqueta anterior."
    assert indice_anterior < indice_despliegue, (
        "Se guarda antes de desplegar, o no hay a dónde volver."
    )


def test_hay_comprobacion_posterior_y_reversion() -> None:
    texto = _texto(WORKFLOW)
    assert "/health" in texto, "Falta la comprobación de que sirve."
    assert "/docs" in texto, "Falta comprobar que /docs está cerrado en producción (SEC.7)."
    assert "systemctl restart govgenai" in texto
    assert "Volviendo a la etiqueta anterior" in texto, (
        "Tiene que existir el camino de vuelta, y decirse en el log."
    )


# ---------------------------------------------------------------------------
# Lo que el despliegue NO hace
# ---------------------------------------------------------------------------


def test_no_se_despliega_con_git_pull_en_la_maquina() -> None:
    texto = _texto(WORKFLOW)
    # Sólo líneas activas: el comentario de cabecera explica por qué NO se hace así.
    activas = [
        l for l in texto.splitlines()
        if "git pull" in l and not l.strip().startswith("#")
    ]
    assert not activas, (
        "Con `git pull` lo que corre depende del estado del disco de la máquina y no de un "
        f"artefacto identificable: {activas}"
    )


def test_el_despliegue_no_ejecuta_la_suite() -> None:
    texto = _texto(WORKFLOW)
    for orden in ("pytest", "npm test", "vitest"):
        activas = [
            l for l in texto.splitlines()
            if orden in l and not l.strip().startswith("#")
        ]
        assert not activas, (
            f"La suite corre en ci.yml sobre el mismo commit; repetirla aquí alarga el "
            f"despliegue sin añadir información: {activas}"
        )


# ---------------------------------------------------------------------------
# Las migraciones, en su servicio
# ---------------------------------------------------------------------------


def test_el_servicio_de_migracion_esta_bajo_perfil_y_no_usa_uv() -> None:
    datos = yaml.safe_load(_texto(COMPOSE))
    migrate = datos["services"]["migrate"]
    assert migrate.get("profiles") == ["migrate"], (
        "Bajo perfil, o `up -d` ejecutaría las migraciones dentro del arranque."
    )
    assert migrate["command"] == ["alembic", "upgrade", "head"], (
        "La imagen de runtime no lleva `uv`: tiene el venv en el PATH. Con `uv run` el "
        "despliegue fallaría con «executable file not found»."
    )
    assert migrate.get("restart") == "no", "Una migración no se reintenta sola."


# ---------------------------------------------------------------------------
# El aprovisionamiento
# ---------------------------------------------------------------------------


def test_el_proveedor_de_identidad_esta_acotado_al_repositorio() -> None:
    texto = _texto(PROVISION)
    assert "--attribute-condition" in texto, (
        "Sin condición de atributo, el proveedor acepta tokens de CUALQUIER repositorio de "
        "GitHub y cualquiera podría suplantar a la cuenta de despliegue."
    )
    assert "assertion.repository==" in texto
    assert "attribute.repository/" in texto, (
        "El binding tiene que ser sobre `attribute.repository/<repo>`, no sobre el pool entero."
    )


def test_el_aprovisionamiento_exige_el_repositorio() -> None:
    texto = _texto(PROVISION)
    assert 'falta --repo' in texto, (
        "El repositorio no puede tener valor por defecto: es lo que acota quién despliega."
    )


def test_la_cuenta_de_despliegue_puede_actuar_como_la_de_la_maquina() -> None:
    """Sin `actAs` sobre la cuenta de la VM, `gcloud compute scp` y `ssh` fallan con
    «User does not have iam.serviceAccounts.actAs permission on the instance's service
    account» — y el mensaje no dice sobre qué cuenta falta el permiso. El segundo despliegue
    real murió aquí.

    Y se concede **sobre esa cuenta**, no a nivel de proyecto: `serviceAccountUser` en el
    proyecto permitiría suplantar a cualquier cuenta de servicio.
    """
    texto = _texto(PROVISION)
    assert "roles/iam.serviceAccountUser" in texto, (
        "Falta el permiso que permite entrar en la máquina."
    )
    assert "VM_SA" in texto, "El permiso tiene que concederse sobre la cuenta de la VM."
    proyecto_entero = [
        l for l in texto.splitlines()
        if "projects add-iam-policy-binding" in l and "serviceAccountUser" in l
    ]
    assert not proyecto_entero, (
        f"`serviceAccountUser` no se concede a nivel de proyecto: {proyecto_entero}"
    )


def test_la_cuenta_de_despliegue_no_es_de_editor_ni_de_propietario() -> None:
    texto = _texto(PROVISION)
    assert "roles/editor" not in texto and "roles/owner" not in texto
    for rol in ("roles/artifactregistry.writer", "roles/iap.tunnelResourceAccessor"):
        assert rol in texto, f"Falta el rol mínimo {rol}"
