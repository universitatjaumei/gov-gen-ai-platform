import pandas as pd
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import select, text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

import client_app.app.database.db as db
from client_app.app.database.models import DatabaseCredentialConfig
from client_app.app.modules.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)

class SQLConnectorService:
    """
    Servicio para gestionar conexiones y ejecutar consultas en bases de datos SQL externas.
    Soporta MySQL, PostgreSQL, SQL Server y SQLite de forma transparente.
    """

    def __init__(self):
        self._engines: Dict[int, AsyncEngine] = {}
        self.encryption = EncryptionService()

    async def get_engine(self, credential_id: int) -> AsyncEngine:
        """
        Obtiene o crea un motor (engine) asíncrono de SQLAlchemy para la credencial dada.
        Mantiene un pool de motores activos para reutilización.

        Args:
            credential_id: ID de la configuración de credenciales de base de datos.

        Returns:
            Instancia de AsyncEngine configurada.
        """
        if credential_id in self._engines:
            return self._engines[credential_id]

        async with AsyncSession(db.client_engine) as session:
            cred = await session.get(DatabaseCredentialConfig, credential_id)
            if not cred:
                raise ValueError(f"Credential {credential_id} not found")

            # Decrypt password
            password = ""
            if cred.encrypted_password:
                try:
                    decrypted_data = self.encryption.decrypt(cred.encrypted_password)
                    if isinstance(decrypted_data, dict):
                        password = decrypted_data.get("password", decrypted_data.get("user_password", ""))
                    else:
                        password = str(decrypted_data)
                except Exception:
                    password = cred.encrypted_password
            
            connection_url = cred.get_connection_string(password)
            
            engine_args = {
                "pool_pre_ping": True  # Verifica la conexión antes de usarla
            }
            if cred.db_type == "sqlite":
                engine_args["connect_args"] = {"check_same_thread": False}
                if ":memory:" in connection_url:
                    engine_args["poolclass"] = StaticPool
                # SQLite doesn't need pool_pre_ping
                engine_args.pop("pool_pre_ping", None)

            engine = create_async_engine(connection_url, **engine_args)
            self._engines[credential_id] = engine
            return engine

    def _format_error_message(self, error: Exception) -> str:
        """Convierte errores técnicos en mensajes amigables para el usuario."""
        err_str = str(error).lower()
        
        # Detectar problemas de red comunes
        network_indicators = [
            "can't connect", "connection refused", "timeout", "network is unreachable",
            "timed out", "connection reset", "name or service not known",
            "could not connect to server", "connection to server at", "was not found",
            "unknown host"
        ]
        
        if any(ind in err_str for ind in network_indicators):
            return "No se puede alcanzar el servidor. ¿Estás conectado a la VPN?"
            
        return f"Error de base de datos: {str(error)}"

    async def test_connection(self, credential_id: int) -> Tuple[bool, str]:
        """
        Prueba la conectividad con la base de datos utilizando las credenciales dadas.

        Args:
            credential_id: ID de la credencial a probar.

        Returns:
            Tupla con (éxito: bool, mensaje: str).
        """
        try:
            engine = await self.get_engine(credential_id)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, "Conectado correctamente a la base de datos"
        except Exception as e:
            logger.error(f"Error testing connection for {credential_id}: {e}")
            msg = self._format_error_message(e)
            return False, msg

    def _is_write_query(self, query: str) -> bool:
        """
        Realiza una comprobación básica para detectar operaciones de escritura o destructivas.
        """
        query_upper = query.strip().upper()
        write_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE ", "ALTER ", "CREATE "]
        return any(query_upper.startswith(kw) for kw in write_keywords)

    async def execute_query(
        self,
        credential_id: int,
        query: str,
        params: dict = None,
        allow_write: bool = False,
        timeout_seconds: int = 30,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Ejecuta una consulta SQL y devuelve los resultados como un DataFrame de pandas.

        Args:
            credential_id: ID de la credencial a utilizar.
            query: Sentencia SQL a ejecutar.
            params: Diccionario de parámetros para la consulta.
            allow_write: Si es False (defecto), bloquea consultas SQL que no sean SELECT.
            timeout_seconds: Tiempo máximo permitido para la ejecución.
            limit: Número máximo de filas a recuperar.

        Returns:
            Pandas DataFrame con los resultados (vacío si no hay filas).
        """
        if not allow_write and self._is_write_query(query):
            raise PermissionError("Write operations not allowed on this query")

        engine = await self.get_engine(credential_id)
        
        try:
            async with engine.connect() as conn:
                async def _run():
                    result = await conn.execute(text(query), params or {})
                    if self._is_write_query(query):
                        await conn.commit()
                    
                    if result.returns_rows:
                        columns = result.keys()
                        # Si hay limit, fetchmany, si no, fetchall
                        if limit:
                            rows = result.fetchmany(limit)
                        else:
                            rows = result.fetchall()
                        return pd.DataFrame([dict(zip(columns, row)) for row in rows])
                    return pd.DataFrame()

                return await asyncio.wait_for(_run(), timeout=timeout_seconds)

        except asyncio.TimeoutError:
            err_msg = f"La consulta ha excedido el tiempo de espera ({timeout_seconds}s)"
            logger.error(err_msg)
            raise TimeoutError(err_msg)
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error executing query on {credential_id}: {e}")
            raise Exception(self._format_error_message(e))
        except Exception as e:
            logger.error(f"Unexpected error executing query on {credential_id}: {e}")
            raise e

    async def get_tables(self, credential_id: int) -> List[str]:
        """
        Obtiene la lista de nombres de tablas disponibles en el esquema de la base de datos.
        Ajusta la consulta según el tipo de motor (MySQL, PG, SQLite, SQLServer).
        """
        async with AsyncSession(db.client_engine) as session:
            cred = await session.get(DatabaseCredentialConfig, credential_id)
            db_type = cred.db_type if cred else "unknown"

        if db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        elif db_type == "mysql":
            query = "SHOW TABLES"
        elif db_type == "postgresql":
            query = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'"
        elif db_type == "sqlserver":
            query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        else:
            return []

        df = await self.execute_query(credential_id, query)
        if df.empty:
            return []
        
        return df.iloc[:, 0].tolist()

    async def get_table_schema(self, credential_id: int, table: str) -> Dict[str, str]:
        """
        Obtiene la estructura de una tabla específica (nombres de columna y tipos de datos).
        """
        df = await self.execute_query(credential_id, f"SELECT * FROM {table} WHERE 1=0")
        return {col: str(df[col].dtype) for col in df.columns}

# Singleton
sql_connector_service = SQLConnectorService()
