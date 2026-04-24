"""
Servicio centralizado de consultas de consumo.

Proporciona capacidades de agregación y consulta sobre los registros de
facturación (BillingRecords). Permite obtener resúmenes detallados para
administradores, partners y clientes finales.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.models import (
    BillingRecord,
    ClientAccount,
    PartnerAccount,
    License,
)


class ConsumptionQueryService:
    """
    Servicio de consultas de consumo para paneles de administración y portales de partner.

    Esta clase encapsula la lógica de agregación SQL para calcular totales de tokens,
    costes en USD y desgloses por modelo de IA, filtrados por diferentes dimensiones
    temporales y jerarquías (Partner -> Cliente -> Licencia).
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def _get_date_range(self, year: int, month: int) -> Tuple[datetime, datetime]:
        """
        Calcula el rango de fechas (inicio y fin) para un mes determinado.

        Args:
            year: Año de la consulta.
            month: Mes (1-12).

        Returns:
            Tuple[datetime, datetime]: (Fecha de inicio, Fecha de fin excluida).
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        return start_date, end_date

    async def get_partner_summary(
        self, partner_id: str, year: int, month: int
    ) -> Dict[str, Any]:
        """
        Calcula el resumen de consumo mensual para un Partner.

        Agrega los datos de todos los clientes pertenecientes a dicho partner y
        proporciona desgloses por cliente y por modelo de IA utilizado.

        Args:
            partner_id: identificador único del Partner.
            year: Año del ejercicio.
            month: Mes del ejercicio.

        Returns:
            Dict[str, Any]: Diccionario con métricas consolidadas (tokens, costes, desgloses).
        """
        start_date, end_date = self._get_date_range(year, month)

        # Total tokens y coste
        stmt = select(
            func.sum(BillingRecord.tokens_used), func.sum(BillingRecord.cost_usd)
        ).where(
            BillingRecord.partner_id == partner_id,
            BillingRecord.timestamp >= start_date,
            BillingRecord.timestamp < end_date,
        )
        result = await self.db.exec(stmt)
        row = result.first()

        total_tokens = row[0] or 0
        total_cost = row[1] or 0.0

        # Por cliente
        by_client = await self._get_by_client(partner_id, start_date, end_date)

        # Por modelo
        by_model = await self._get_by_model(
            partner_id=partner_id, start_date=start_date, end_date=end_date
        )

        return {
            "partner_id": partner_id,
            "year": year,
            "month": month,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "by_client": by_client,
            "by_model": by_model,
        }

    async def get_client_summary(
        self, client_id: str, year: int, month: int
    ) -> Dict[str, Any]:
        """
        Calcula el resumen de consumo mensual para un Cliente específico.

        Args:
            client_id: Identificador del cliente final.
            year: Año de la consulta.
            month: Mes de la consulta.

        Returns:
            Dict[str, Any]: Métricas de uso y lista de operaciones recientes.
        """
        start_date, end_date = self._get_date_range(year, month)

        # Total tokens y coste
        stmt = select(
            func.sum(BillingRecord.tokens_used), func.sum(BillingRecord.cost_usd)
        ).where(
            BillingRecord.client_id == client_id,
            BillingRecord.timestamp >= start_date,
            BillingRecord.timestamp < end_date,
        )
        result = await self.db.exec(stmt)
        row = result.first()

        total_tokens = row[0] or 0
        total_cost = row[1] or 0.0

        # Por modelo
        by_model = await self._get_by_model(
            client_id=client_id, start_date=start_date, end_date=end_date
        )

        # Últimas operaciones
        recent_ops = await self.get_recent_operations(client_id=client_id, limit=10)

        return {
            "client_id": client_id,
            "year": year,
            "month": month,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "by_model": by_model,
            "recent_operations": recent_ops,
        }

    async def get_license_summary(self, license_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de consumo actual de una Licencia de software.

        Calcula el porcentaje de uso respecto a la cuota contratada y recupera
        la información del cliente propietario.

        Args:
            license_id: UUID de la licencia en la base de datos.

        Returns:
            Dict[str, Any]: Datos de cuota, consumo y auditoría de uso.
        """
        # Obtener licencia
        license = await self.db.get(License, license_id)
        if not license:
            return {"error": "Licencia no encontrada"}

        # Obtener cliente para el partner_id
        client = await self.db.get(ClientAccount, license.client_id)

        # Calcular coste total acumulado desde BillingRecord
        stmt = select(
            func.sum(BillingRecord.tokens_used), func.sum(BillingRecord.cost_usd)
        ).where(BillingRecord.client_id == license.client_id)
        result = await self.db.exec(stmt)
        row = result.first()
        total_cost = row[1] or 0.0

        # Últimas operaciones
        recent_ops = await self.get_recent_operations(
            client_id=license.client_id, limit=20
        )

        return {
            "license_id": license_id,
            "client_id": license.client_id,
            "client_name": client.name if client else "Unknown",
            "quota_tokens": license.quota_tokens,
            "consumed_tokens": license.consumed_tokens,
            "remaining_tokens": license.quota_tokens - license.consumed_tokens,
            "usage_percent": round(
                (license.consumed_tokens / license.quota_tokens) * 100, 1
            )
            if license.quota_tokens > 0
            else 0,
            "total_cost_usd": round(total_cost, 4),
            "recent_operations": recent_ops,
        }

    async def get_recent_operations(
        self,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las últimas operaciones de billing.
        """
        stmt = select(BillingRecord).order_by(BillingRecord.timestamp.desc())

        if client_id:
            stmt = stmt.where(BillingRecord.client_id == client_id)
        elif partner_id:
            stmt = stmt.where(BillingRecord.partner_id == partner_id)

        stmt = stmt.limit(limit)

        result = await self.db.exec(stmt)
        records = result.all()

        return [
            {
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M"),
                "operation": r.operation,
                "model_id": r.model_id,
                "tokens_used": r.tokens_used,
                "cost_usd": round(r.cost_usd, 6),
            }
            for r in records
        ]

    async def _get_by_client(
        self, partner_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Desglose de consumo por cliente."""
        stmt = (
            select(
                BillingRecord.client_id,
                func.sum(BillingRecord.tokens_used).label("tokens"),
                func.sum(BillingRecord.cost_usd).label("cost"),
            )
            .where(
                BillingRecord.partner_id == partner_id,
                BillingRecord.timestamp >= start_date,
                BillingRecord.timestamp < end_date,
            )
            .group_by(BillingRecord.client_id)
        )

        result = await self.db.exec(stmt)
        rows = result.all()

        output = []
        for row in rows:
            client = await self.db.get(ClientAccount, row.client_id)
            output.append(
                {
                    "client_id": row.client_id,
                    "client_name": client.name if client else "Unknown",
                    "tokens": row.tokens or 0,
                    "cost_usd": round(row.cost or 0, 4),
                }
            )

        return sorted(output, key=lambda x: x["tokens"], reverse=True)

    async def _get_by_model(
        self,
        partner_id: Optional[str] = None,
        client_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Desglose de consumo por modelo."""
        stmt = select(
            BillingRecord.model_id,
            func.sum(BillingRecord.tokens_used).label("tokens"),
            func.sum(BillingRecord.cost_usd).label("cost"),
        )

        if partner_id:
            stmt = stmt.where(BillingRecord.partner_id == partner_id)
        if client_id:
            stmt = stmt.where(BillingRecord.client_id == client_id)
        if start_date:
            stmt = stmt.where(BillingRecord.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(BillingRecord.timestamp < end_date)

        stmt = stmt.group_by(BillingRecord.model_id)

        result = await self.db.exec(stmt)
        rows = result.all()

        return [
            {
                "model_id": row.model_id or "unknown",
                "tokens": row.tokens or 0,
                "cost_usd": round(row.cost or 0, 4),
            }
            for row in sorted(rows, key=lambda x: x.tokens or 0, reverse=True)
        ]

    async def get_all_partners_summary(
        self, year: int, month: int
    ) -> List[Dict[str, Any]]:
        """
        Resumen de consumo de todos los partners (para superadmin).
        """
        start_date, end_date = self._get_date_range(year, month)

        stmt = (
            select(
                BillingRecord.partner_id,
                func.sum(BillingRecord.tokens_used).label("tokens"),
                func.sum(BillingRecord.cost_usd).label("cost"),
            )
            .where(
                BillingRecord.timestamp >= start_date,
                BillingRecord.timestamp < end_date,
            )
            .group_by(BillingRecord.partner_id)
        )

        result = await self.db.exec(stmt)
        rows = result.all()

        output = []
        for row in rows:
            partner = await self.db.get(PartnerAccount, row.partner_id)
            output.append(
                {
                    "partner_id": row.partner_id,
                    "partner_name": partner.name if partner else "Unknown",
                    "tokens": row.tokens or 0,
                    "cost_usd": round(row.cost or 0, 4),
                }
            )

        return sorted(output, key=lambda x: x["tokens"], reverse=True)
