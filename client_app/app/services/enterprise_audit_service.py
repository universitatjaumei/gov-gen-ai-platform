import pandas as pd
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
import client_app.app.database.db as db
from automatia_shared.core.audit_models import EnterpriseAuditLog, RiskLevel

# ReportLab imports for PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

class EnterpriseAuditService:
    """
    Servicio para gestionar el registro y consulta de logs de auditoría enterprise.
    Proporciona trazabilidad inmutable de operaciones PII y seguridad.
    """

    async def log_event(
        self,
        action_type: str,
        module: str,
        user_id: str = None,
        pii_metrics: Dict = None,
        source_description: str = None,
        target_description: str = None,
        risk_level: str = RiskLevel.LOW.value,
        **kwargs
    ) -> EnterpriseAuditLog:
        """
        Registra un evento de auditoría detallado en la base de datos local del cliente.
        Captura métricas de PII, niveles de riesgo y contexto adicional (IDs de ejecución, etc.).

        Args:
            action_type: Tipo de acción (LOGIN, DOWNLOAD, EXECUTION, etc.).
            module: Módulo que genera el evento.
            user_id: ID del usuario que realiza la acción.
            pii_metrics: Diccionario con métricas de detección/protección de datos sensibles.
            source_description: Descripción del origen de los datos.
            target_description: Descripción del destino de los datos.
            risk_level: Nivel de riesgo detectado.
            **kwargs: Parámetros adicionales como execution_id, task_log_id, etc.

        Returns:
            El objeto EnterpriseAuditLog persistido.
        """
        async with AsyncSession(db.client_engine) as session:
            audit = EnterpriseAuditLog(
                action_type=action_type,
                module=module,
                user_id=user_id,
                pii_detected_count=pii_metrics.get("detected", 0) if pii_metrics else 0,
                pii_protected_count=pii_metrics.get("protected", 0) if pii_metrics else 0,
                pii_types=pii_metrics.get("types", {}) if pii_metrics else {},
                anonymization_method=pii_metrics.get("method") if pii_metrics else None,
                source_description=source_description,
                target_description=target_description,
                risk_level=risk_level,
                execution_id=kwargs.get("execution_id"),
                task_log_id=kwargs.get("task_log_id"),
                additional_context=kwargs.get("additional_context", {}),
                security_flags=kwargs.get("security_flags", {})
            )
            session.add(audit)
            await session.commit()
            await session.refresh(audit)
            return audit

    async def log_pii_operation(
        self,
        operation: str,
        pii_types: Dict[str, int],
        method: str = None,
        **kwargs
    ) -> EnterpriseAuditLog:
        """
        Registra específicamente operaciones que involucran datos sensibles (PII).
        Calcula automáticamente contadores de detección y protección basados en pii_types.

        Args:
            operation: Nombre de la operación PII (ej. 'MASKING', 'ENCRYPTION').
            pii_types: Diccionario con los tipos de PII detectados y su conteo.
            method: Método técnico utilizado para proteger la información.
        """
        detected = sum(pii_types.values())
        # Extract module from kwargs to avoid duplicate parameter
        module = kwargs.pop("module", "privacy_service")
        return await self.log_event(
            action_type=operation,
            module=module,
            pii_metrics={
                "detected": detected,
                "protected": detected,  # Por defecto asumimos éxito en la protección
                "types": pii_types,
                "method": method
            },
            **kwargs
        )

    async def query_logs(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        user_id: str = None,
        action_type: str = None,
        risk_level: str = None,
        module: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[EnterpriseAuditLog]:
        """
        Consulta y filtra registros de auditoría aplicando múltiples criterios de búsqueda.

        Args:
            start_date: Fecha de inicio para el rango temporal.
            end_date: Fecha de fin para el rango temporal.
            user_id: Filtrar por usuario.
            action_type: Filtrar por tipo de acción.
            risk_level: Filtrar por nivel de riesgo.
            module: Filtrar por módulo.
            limit: Número máximo de registros a retornar.
            offset: Desplazamiento para paginación.

        Returns:
            Una lista de objetos EnterpriseAuditLog ordenados cronológicamente DESC.
        """
        async with AsyncSession(db.client_engine) as session:
            statement = select(EnterpriseAuditLog)
            
            if start_date:
                statement = statement.where(EnterpriseAuditLog.timestamp >= start_date)
            if end_date:
                statement = statement.where(EnterpriseAuditLog.timestamp <= end_date)
            if user_id:
                statement = statement.where(EnterpriseAuditLog.user_id == user_id)
            if action_type:
                statement = statement.where(EnterpriseAuditLog.action_type == action_type)
            if risk_level:
                statement = statement.where(EnterpriseAuditLog.risk_level == risk_level)
            if module:
                statement = statement.where(EnterpriseAuditLog.module == module)
                
            # Orden descendente por defecto
            statement = statement.order_by(EnterpriseAuditLog.timestamp.desc()).offset(offset).limit(limit)
            
            result = await session.exec(statement)
            return result.all()

    async def get_summary_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Calcula estadísticas agregadas de auditoría para un periodo de tiempo determinado.

        Returns:
            Diccionario con total_count, high_risk_count, pii_processed y el string del periodo.
        """
        logs = await self.query_logs(start_date=start_date, end_date=end_date, limit=10000)
        
        total_count = len(logs)
        high_risk_count = sum(1 for log in logs if log.risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value])
        pii_processed = sum(log.pii_detected_count for log in logs)
        
        return {
            "total_count": total_count,
            "high_risk_count": high_risk_count,
            "pii_processed": pii_processed,
            "period": f"{start_date.date()} - {end_date.date()}"
        }

    async def generate_excel_export(self, logs: List[EnterpriseAuditLog], stats: Dict[str, Any]) -> io.BytesIO:
        """
        Exporta una lista de logs y sus estadísticas de resumen a un archivo Excel (.xlsx).
        Procesa campos complejos para que sean legibles en hojas de cálculo.
        """
        output = io.BytesIO()
        
        # DataFrame de logs
        data = []
        for log in logs:
            d = log.model_dump()
            # Convertir dicts complejos a string para Excel
            d['pii_types'] = str(d['pii_types'])
            d['additional_context'] = str(d['additional_context'])
            d['security_flags'] = str(d['security_flags'])
            data.append(d)
        
        df_logs = pd.DataFrame(data)
        
        # DataFrame de estadísticas
        df_stats = pd.DataFrame([stats])
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_logs.to_excel(writer, sheet_name='Logs Auditoría', index=False)
            df_stats.to_excel(writer, sheet_name='Resumen', index=False)
            
        output.seek(0)
        return output

    async def generate_pdf_export(self, logs: List[EnterpriseAuditLog], stats: Dict[str, Any], translations: Dict[str, str]) -> io.BytesIO:
        """
        Genera un informe PDF profesional con tablas formateadas y KPIs de seguridad.
        Utiliza traducciones dinámicas para soportar múltiples idiomas en el reporte.
        """
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=20)
        elements.append(Paragraph(translations.get('audit_export_report_title', 'Audit Report'), title_style))
        
        # Resumen (KPIs)
        elements.append(Paragraph(translations.get('audit_export_summary', 'Summary'), styles['Heading2']))
        summary_data = [
            [translations.get('audit_stats_total', 'Total'), translations.get('audit_stats_high_risk', 'High Risk'), translations.get('audit_stats_pii', 'PII Protected'), translations.get('audit_filter_date', 'Period')],
            [stats['total_count'], stats['high_risk_count'], stats['pii_processed'], stats['period']]
        ]
        summary_table = Table(summary_data, colWidths=[5*cm, 5*cm, 5*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Tabla de Logs
        elements.append(Paragraph("LOGS DETAIL", styles['Heading2']))
        
        header = [
            translations.get('audit_col_timestamp', 'Timestamp'),
            translations.get('audit_col_action', 'Action'),
            translations.get('audit_col_user', 'User'),
            translations.get('audit_col_pii', 'PII'),
            translations.get('audit_col_risk', 'Risk'),
            translations.get('audit_filter_module', 'Module')
        ]
        
        log_rows = [header]
        for log in logs:
            log_rows.append([
                log.timestamp.strftime('%Y-%m-%d %H:%M'),
                log.action_type,
                log.user_id or 'System',
                f"{log.pii_protected_count}/{log.pii_detected_count}",
                log.risk_level.upper(),
                log.module
            ])
            
        logs_table = Table(log_rows, colWidths=[4*cm, 4*cm, 4*cm, 3*cm, 3*cm, 5*cm], repeatRows=1)
        logs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        
        elements.append(logs_table)
        
        doc.build(elements)
        output.seek(0)
        return output

# Instancia singleton para uso en la aplicación
enterprise_audit_service = EnterpriseAuditService()
