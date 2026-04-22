# client_app/app/modules/security/policy_manager.py
"""
PartnerPolicyManager - Gestión de políticas de seguridad dinámicas.

Aplica políticas de seguridad por Partner/Cliente con cascada:
Partner > Cliente > Sistema

Permite configurar:
- Imports permitidos/prohibidos
- Timeout de ejecución
- Límite de memoria
"""
from typing import Dict, Any, Optional, Set, List
import json
from automatia_shared.core.security import SecurityAuditor, SAFE_IMPORTS


class PartnerPolicyManager:
    """
    Gestiona políticas de seguridad con cascada: Partner > Cliente > Sistema.

    La cascada funciona así:
    1. Si Partner define un valor, ese gana
    2. Si no, si Cliente lo define, ese se usa
    3. Si ninguno, se usa el default del sistema

    Uso:
        # Solo con política de cliente
        mgr = PartnerPolicyManager(client_policy={"max_execution_time": 60})

        # Con cascada Partner > Cliente
        mgr = PartnerPolicyManager(
            client_policy={"max_execution_time": 120},
            partner_policy={"max_execution_time": 60}
        )

        # Aplicar al auditor
        auditor = SecurityAuditor()
        mgr.apply_to_auditor(auditor)
    """

    # Defaults del sistema (fallback final)
    SYSTEM_DEFAULTS: Dict[str, Any] = {
        "max_execution_time": 300,  # 5 minutos
        "max_memory_mb": 512,
        "allowed_imports": list(SAFE_IMPORTS),
        "forbidden_imports": [],
    }

    def __init__(
        self,
        client_policy: Optional[Dict[str, Any]] = None,
        partner_policy: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa el manager con políticas opcionales.

        Args:
            client_policy: Política del cliente (nivel 2 en cascada)
            partner_policy: Política del partner (nivel 1, máxima prioridad)
        """
        self._client = client_policy or {}
        self._partner = partner_policy or {}

    def _get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene valor con cascada: Partner > Cliente > Sistema.

        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe en ningún nivel

        Returns:
            Valor de la configuración según cascada
        """
        # Partner tiene máxima prioridad
        if key in self._partner:
            return self._partner[key]
        # Cliente es segundo nivel
        if key in self._client:
            return self._client[key]
        # Sistema es fallback
        return self.SYSTEM_DEFAULTS.get(key, default)

    def apply_to_auditor(self, auditor: SecurityAuditor) -> None:
        """
        Aplica restricciones adicionales al auditor de seguridad.

        Los imports prohibidos de la política se añaden al conjunto
        unsafe_imports del auditor.

        Args:
            auditor: Instancia de SecurityAuditor a modificar
        """
        forbidden = self._get("forbidden_imports", [])
        for imp in forbidden:
            auditor.unsafe_imports.add(imp)

    def get_timeout(self) -> int:
        """
        Obtiene timeout máximo de ejecución en segundos.

        Returns:
            Timeout en segundos (default: 300)
        """
        return self._get("max_execution_time", 300)

    def get_memory_limit(self) -> int:
        """
        Obtiene límite de memoria en MB.

        Returns:
            Límite de memoria en MB (default: 512)
        """
        return self._get("max_memory_mb", 512)

    def get_allowed_imports(self) -> Set[str]:
        """
        Obtiene imports permitidos (intersección con SAFE_IMPORTS base).

        Los imports permitidos son la intersección entre:
        1. Lo que permite la política (si especifica allowed_imports)
        2. Lo que permite SAFE_IMPORTS (whitelist base del sistema)

        Returns:
            Set de nombres de módulos permitidos
        """
        policy_allowed = set(self._get("allowed_imports", []))
        # Solo permitir lo que esté en ambos: política Y whitelist base
        return policy_allowed.intersection(SAFE_IMPORTS)

    def get_forbidden_imports(self) -> List[str]:
        """
        Obtiene lista de imports explícitamente prohibidos.

        Returns:
            Lista de nombres de módulos prohibidos
        """
        return self._get("forbidden_imports", [])

    def get_effective_policy(self) -> Dict[str, Any]:
        """
        Devuelve la política efectiva (todos los valores resueltos).

        Útil para debugging y logging.

        Returns:
            Diccionario con toda la configuración efectiva
        """
        return {
            "max_execution_time": self.get_timeout(),
            "max_memory_mb": self.get_memory_limit(),
            "allowed_imports": list(self.get_allowed_imports()),
            "forbidden_imports": self.get_forbidden_imports(),
        }

    @classmethod
    def from_db(cls, session, policy_name: str) -> "PartnerPolicyManager":
        """
        Carga política desde el modelo SecurityPolicy en base de datos.

        Args:
            session: Sesión de SQLModel/SQLAlchemy
            policy_name: Nombre de la política a cargar

        Returns:
            Instancia de PartnerPolicyManager con la política cargada
        """
        from client_app.app.database.models import SecurityPolicy

        policy = session.query(SecurityPolicy).filter_by(name=policy_name).first()
        if not policy:
            # Retornar manager con defaults del sistema
            return cls()

        # Parsear JSON de los campos de la política
        try:
            allowed_imports = json.loads(policy.allowed_imports)
        except (json.JSONDecodeError, TypeError):
            allowed_imports = []

        try:
            forbidden_imports = json.loads(policy.forbidden_imports)
        except (json.JSONDecodeError, TypeError):
            forbidden_imports = []

        return cls(client_policy={
            "max_execution_time": policy.max_execution_time,
            "max_memory_mb": policy.max_memory_mb,
            "allowed_imports": allowed_imports,
            "forbidden_imports": forbidden_imports,
        })

    @classmethod
    def from_db_with_cascade(
        cls,
        session,
        client_policy_name: Optional[str] = None,
        partner_policy_name: Optional[str] = None
    ) -> "PartnerPolicyManager":
        """
        Carga políticas de cliente y partner desde BD con cascada.

        Args:
            session: Sesión de SQLModel/SQLAlchemy
            client_policy_name: Nombre de la política del cliente
            partner_policy_name: Nombre de la política del partner

        Returns:
            Instancia con cascada configurada
        """
        from client_app.app.database.models import SecurityPolicy

        client_policy: Dict[str, Any] = {}
        partner_policy: Dict[str, Any] = {}

        # Cargar política del cliente
        if client_policy_name:
            cp = session.query(SecurityPolicy).filter_by(name=client_policy_name).first()
            if cp:
                client_policy = {
                    "max_execution_time": cp.max_execution_time,
                    "max_memory_mb": cp.max_memory_mb,
                    "allowed_imports": json.loads(cp.allowed_imports or "[]"),
                    "forbidden_imports": json.loads(cp.forbidden_imports or "[]"),
                }

        # Cargar política del partner
        if partner_policy_name:
            pp = session.query(SecurityPolicy).filter_by(name=partner_policy_name).first()
            if pp:
                partner_policy = {
                    "max_execution_time": pp.max_execution_time,
                    "max_memory_mb": pp.max_memory_mb,
                    "allowed_imports": json.loads(pp.allowed_imports or "[]"),
                    "forbidden_imports": json.loads(pp.forbidden_imports or "[]"),
                }

        return cls(client_policy=client_policy, partner_policy=partner_policy)

    def __repr__(self) -> str:
        return (
            f"PartnerPolicyManager("
            f"timeout={self.get_timeout()}s, "
            f"memory={self.get_memory_limit()}MB, "
            f"allowed={len(self.get_allowed_imports())}, "
            f"forbidden={len(self.get_forbidden_imports())})"
        )
