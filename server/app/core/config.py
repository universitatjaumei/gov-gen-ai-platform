"""
Server core configuration.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    environment: str
    # Sandbox (script-sandbox microservice — SBX.1/SBX.2)
    sandbox_base_url: str = "http://script-sandbox:5000"
    sandbox_timeout_seconds_default: int = 30
    sandbox_connect_timeout_seconds: float = 5.0
    sandbox_max_retries_on_connect_error: int = 1
    sandbox_mode: str = "http"
    # Content quality scheduler (9Q.5)
    content_quality_enabled: bool = True
    content_quality_interval_hours: int = 24
    content_quality_semantic_enabled: bool = True
    # Cortesía del rastreo (RAS.1) — quien vea el tráfico en sus registros tiene que poder
    # saber quién es y a quién escribir. Va en el User-Agent de cada petición.
    crawler_contact: str = ""
    # SSO SAML (AUTH.1) — Service Provider genérico SAML 2.0
    saml_enabled: bool = False
    saml_sp_entity_id: str = ""
    saml_sp_acs_url: str = ""
    saml_sp_sls_url: str = ""
    saml_sp_x509_cert: str = ""
    saml_sp_private_key: str = ""
    saml_idp_metadata_url: str = ""
    saml_idp_metadata_xml: str = ""
    saml_attr_email: str = "mail"
    saml_attr_name: str = "displayName"
    saml_attr_role: str = "role"
    saml_attr_groups: str = "groups"
    saml_group_role_map: str = ""
    saml_default_role: str = "user"
    saml_frontend_return_url: str = ""
    # SEC.2.1: la organización a la que pertenece este IdP. Sale de aquí y NUNCA de la
    # aserción: si viniera de fuera, quien controla el IdP podría declarar a qué
    # organización pertenece cada persona que entra.
    saml_organizacion_id: str = ""
    # Subidas (SEC.6) — límite de tamaño y cuota de documentos por chatbot
    max_upload_mb: int = 10
    max_documents_per_chatbot: int = 0  # 0 = sin límite

    @property
    def is_dev_mode(self) -> bool:
        return self.environment == "development"


def get_settings() -> Settings:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    # sandbox_mode defaults to "local" when TESTING=1 to avoid Docker dependency in CI.
    default_sandbox_mode = "local" if os.getenv("TESTING") == "1" else "http"
    ajustes = Settings(
        jwt_secret_key=secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
        environment=os.getenv("ENVIRONMENT", "development"),
        sandbox_base_url=os.getenv("SANDBOX_BASE_URL", "http://script-sandbox:5000"),
        sandbox_timeout_seconds_default=int(os.getenv("SANDBOX_TIMEOUT_SECONDS_DEFAULT", "30")),
        sandbox_connect_timeout_seconds=float(os.getenv("SANDBOX_CONNECT_TIMEOUT_SECONDS", "5.0")),
        sandbox_max_retries_on_connect_error=int(
            os.getenv("SANDBOX_MAX_RETRIES_ON_CONNECT_ERROR", "1")
        ),
        sandbox_mode=os.getenv("SANDBOX_MODE", default_sandbox_mode),
        content_quality_enabled=os.getenv("CONTENT_QUALITY_ENABLED", "true").lower() != "false",
        content_quality_interval_hours=int(os.getenv("CONTENT_QUALITY_INTERVAL_HOURS", "24")),
        content_quality_semantic_enabled=os.getenv("CONTENT_QUALITY_SEMANTIC_ENABLED", "true").lower() != "false",
        crawler_contact=os.getenv("CRAWLER_CONTACT", ""),
        saml_enabled=os.getenv("SAML_ENABLED", "false").lower() == "true",
        saml_sp_entity_id=os.getenv("SAML_SP_ENTITY_ID", ""),
        saml_sp_acs_url=os.getenv("SAML_SP_ACS_URL", ""),
        saml_sp_sls_url=os.getenv("SAML_SP_SLS_URL", ""),
        saml_sp_x509_cert=os.getenv("SAML_SP_X509_CERT", ""),
        saml_sp_private_key=os.getenv("SAML_SP_PRIVATE_KEY", ""),
        saml_idp_metadata_url=os.getenv("SAML_IDP_METADATA_URL", ""),
        saml_idp_metadata_xml=os.getenv("SAML_IDP_METADATA_XML", ""),
        saml_attr_email=os.getenv("SAML_ATTR_EMAIL", "mail"),
        saml_attr_name=os.getenv("SAML_ATTR_NAME", "displayName"),
        saml_attr_role=os.getenv("SAML_ATTR_ROLE", "role"),
        saml_attr_groups=os.getenv("SAML_ATTR_GROUPS", "groups"),
        saml_group_role_map=os.getenv("SAML_GROUP_ROLE_MAP", ""),
        saml_default_role=os.getenv("SAML_DEFAULT_ROLE", "user"),
        saml_frontend_return_url=os.getenv("SAML_FRONTEND_RETURN_URL", ""),
        saml_organizacion_id=os.getenv("SAML_ORGANIZACION_ID", ""),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "10")),
        max_documents_per_chatbot=int(os.getenv("MAX_DOCUMENTS_PER_CHATBOT", "0")),
    )
    _assert_configuracion_de_produccion(ajustes)
    return ajustes


_SECRETOS_DE_EJEMPLO = frozenset({
    "change-me-in-production",
    "changeme",
    "secret",
    "test-secret-key",
})


def _assert_configuracion_de_produccion(ajustes: Settings) -> None:
    """Combinaciones que en producción son un fallo de configuración, no una opción.

    Fallar al arrancar es deliberado: `SANDBOX_MODE=local` no da ningún síntoma visible
    —los scripts se ejecutan y devuelven su resultado— mientras corre en el host del
    servidor, con su red y heredando `os.environ`: `JWT_SECRET_KEY`, `DATABASE_URL` y las
    claves de los proveedores quedan al alcance del script. Un despliegue así funciona
    perfectamente hasta que alguien lo aprovecha.
    """
    if ajustes.environment != "production":
        return

    # SEC.8.4: la variable era obligatoria desde SEC.1, pero nada impedía desplegar con el
    # valor de ejemplo del `.env.example`, que está publicado en el repositorio. Un secreto
    # conocido permite firmar tokens de cualquier rol y organización.
    secreto = ajustes.jwt_secret_key or ""
    if secreto.lower() in _SECRETOS_DE_EJEMPLO or len(secreto) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY no puede ser el valor de ejemplo ni tener menos de 32 "
            "caracteres en producción: con él se firman los tokens de todos los roles."
        )

    if ajustes.sandbox_mode == "local":
        raise RuntimeError(
            "SANDBOX_MODE=local ejecuta los scripts en el host del servidor y les entrega "
            "las variables de entorno del proceso. En producción usa el sandbox aislado "
            "(SANDBOX_MODE=http, servicio script-sandbox)."
        )
