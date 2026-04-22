from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
import csv
from io import StringIO

from server.app.database.models import BillingRecord, ClientAccount

class PartnerBillingService:
    """
    Servicio de facturación diseñado para el portal de Partners.
    
    A diferencia del servicio de consulta general, esta clase está vinculada a 
    un `partner_id` específico y proporciona utilidades de exportación (CSV), 
    análisis de tendencias históricas y alertas preventivas de consumo.
    """

    def __init__(self, db_session: AsyncSession, partner_id: str):
        self.db = db_session
        self.partner_id = partner_id

    async def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Obtiene el resumen consolidado de consumo mensual para el Partner.

        Args:
            year: Año natural.
            month: Mes natural (1-12).

        Returns:
            Dict[str, Any]: Resumen con totales y desgloses por cliente/modelo.
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Total tokens y coste
        stmt = select(
            func.sum(BillingRecord.tokens_used),
            func.sum(BillingRecord.cost_usd)
        ).where(
            BillingRecord.partner_id == self.partner_id,
            BillingRecord.timestamp >= start_date,
            BillingRecord.timestamp < end_date
        )
        result = await self.db.exec(stmt)
        row = result.first()

        total_tokens = row[0] or 0
        total_cost = row[1] or 0.0

        # Por cliente
        by_client = await self.get_consumption_by_client(year, month)

        # Por modelo
        by_model = await self.get_consumption_by_model(year, month)

        return {
            "year": year,
            "month": month,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "by_client": by_client,
            "by_model": by_model
        }

    async def get_consumption_by_client(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Calcula el desglose de consumo individual para cada cliente del Partner.

        Args:
            year: Año del ejercicio.
            month: Mes del ejercicio.

        Returns:
            List[Dict]: Lista de clientes con sus respectivos consumos de tokens y costes.
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        stmt = select(
            BillingRecord.client_id,
            func.sum(BillingRecord.tokens_used).label("tokens"),
            func.sum(BillingRecord.cost_usd).label("cost")
        ).where(
            BillingRecord.partner_id == self.partner_id,
            BillingRecord.timestamp >= start_date,
            BillingRecord.timestamp < end_date
        ).group_by(BillingRecord.client_id)

        result = await self.db.exec(stmt)
        rows = result.all()

        # Obtener nombres de clientes
        output = []
        for row in rows:
            client = await self.db.get(ClientAccount, row.client_id)
            output.append({
                "client_id": row.client_id,
                "client_name": client.name if client else "Unknown",
                "tokens": row.tokens or 0,
                "cost_usd": round(row.cost or 0, 4)
            })

        return sorted(output, key=lambda x: x["tokens"], reverse=True)

    async def get_consumption_by_model(self, year: int, month: int) -> List[Dict[str, Any]]:
        """Desglose por modelo de IA."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        stmt = select(
            BillingRecord.model_id,
            func.sum(BillingRecord.tokens_used).label("tokens"),
            func.sum(BillingRecord.cost_usd).label("cost")
        ).where(
            BillingRecord.partner_id == self.partner_id,
            BillingRecord.timestamp >= start_date,
            BillingRecord.timestamp < end_date
        ).group_by(BillingRecord.model_id)

        result = await self.db.exec(stmt)
        rows = result.all()

        return [
            {
                "model_id": row.model_id,
                "tokens": row.tokens or 0,
                "cost_usd": round(row.cost or 0, 4)
            }
            for row in rows
        ]

    async def get_consumption_trend(self, months: int = 6) -> List[Dict[str, Any]]:
        """
        Calcula la tendencia de consumo retroactiva del Partner.

        Args:
            months: Número de meses anteriores a incluir en el análisis.

        Returns:
            List[Dict]: Serie temporal con datos de tokens y costes.
        """
        trend = []
        now = datetime.utcnow()

        for i in range(months - 1, -1, -1):
            # Calcular mes
            target_date = now - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month

            summary = await self.get_monthly_summary(year, month)
            trend.append({
                "month": f"{year}-{month:02d}",
                "tokens": summary["total_tokens"],
                "cost_usd": summary["total_cost_usd"]
            })

        return trend

    async def export_to_csv(self, year: int, month: int) -> str:
        """
        Genera un informe detallado de consumo en formato CSV.

        Args:
            year: Año del informe.
            month: Mes del informe.

        Returns:
            str: Contenido del archivo CSV listo para descarga.
        """
        by_client = await self.get_consumption_by_client(year, month)

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["client_id", "client_name", "tokens", "cost_usd"])

        for item in by_client:
            writer.writerow([
                item["client_id"],
                item["client_name"],
                item["tokens"],
                item["cost_usd"]
            ])

        return output.getvalue()

    async def get_high_consumption_alerts(self, threshold_percent: int = 150) -> List[Dict[str, Any]]:
        """
        Detecta anomalías de consumo en los clientes del Partner.
        
        Compara el consumo del mes actual con el promedio de los últimos 3 meses 
        para detectar picos inusuales que superen un umbral definido.

        Args:
            threshold_percent: Porcentaje sobre la media que dispara la alerta.

        Returns:
            List[Dict]: Lista de clientes con consumos anómalos.
        """
        # Promedio de los ultimos 3 meses por cliente
        now = datetime.utcnow()
        three_months_ago = now - timedelta(days=90)

        # Consumo promedio historico
        stmt_avg = select(
            BillingRecord.client_id,
            (func.sum(BillingRecord.tokens_used) / 3).label("avg_tokens")
        ).where(
            BillingRecord.partner_id == self.partner_id,
            BillingRecord.timestamp >= three_months_ago,
            BillingRecord.timestamp < now.replace(day=1)
        ).group_by(BillingRecord.client_id)

        result_avg = await self.db.exec(stmt_avg)
        avg_map = {row.client_id: row.avg_tokens or 0 for row in result_avg.all()}

        # Consumo este mes
        current_month = await self.get_consumption_by_client(now.year, now.month)

        alerts = []
        for item in current_month:
            avg = avg_map.get(item["client_id"], 0)
            if avg > 0:
                percent = (item["tokens"] / avg) * 100
                if percent >= threshold_percent:
                    alerts.append({
                        "client_id": item["client_id"],
                        "client_name": item["client_name"],
                        "current_consumption": item["tokens"],
                        "average_consumption": int(avg),
                        "percent_increase": round(percent, 1)
                    })

        return sorted(alerts, key=lambda x: x["percent_increase"], reverse=True)
