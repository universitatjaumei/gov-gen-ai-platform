import pytest
from datetime import datetime, timedelta
from server.app.services.partner_billing_service import PartnerBillingService
from server.app.database.models import BillingRecord, ClientAccount

@pytest.mark.asyncio
async def test_monthly_summary(db_session):
    """Obtener resumen de consumo mensual."""
    # Setup
    now = datetime.utcnow()
    # Records for this month
    b1 = BillingRecord(partner_id="p1", client_id="c1", operation="OP1", tokens_used=100, cost_usd=0.1, model_id="m1", timestamp=datetime(2026, 1, 10))
    b2 = BillingRecord(partner_id="p1", client_id="c2", operation="OP2", tokens_used=200, cost_usd=0.2, model_id="m2", timestamp=datetime(2026, 1, 15))
    # Record for another partner
    b3 = BillingRecord(partner_id="p2", client_id="c3", operation="OP3", tokens_used=500, cost_usd=0.5, model_id="m1", timestamp=datetime(2026, 1, 10))
    
    db_session.add_all([b1, b2, b3])
    
    # Need clients for names
    c1 = ClientAccount(client_id="c1", partner_id="p1", name="C1", license_key="k1")
    c2 = ClientAccount(client_id="c2", partner_id="p1", name="C2", license_key="k2")
    db_session.add_all([c1, c2])
    
    await db_session.commit()

    service = PartnerBillingService(db_session, partner_id="p1")
    summary = await service.get_monthly_summary(year=2026, month=1)

    assert summary["total_tokens"] == 300
    assert summary["total_cost_usd"] == 0.3
    
    # Check by client structure
    assert len(summary["by_client"]) == 2
    assert summary["by_client"][0]["tokens"] == 200 # Sort desc

@pytest.mark.asyncio
async def test_consumption_by_model(db_session):
    """Desglose de consumo por modelo de IA."""
    b1 = BillingRecord(partner_id="p1", client_id="c1", operation="OP1", tokens_used=100, cost_usd=0.1, model_id="gpt-4", timestamp=datetime(2026, 1, 10))
    b2 = BillingRecord(partner_id="p1", client_id="c1", operation="OP2", tokens_used=50, cost_usd=0.05, model_id="gpt-4", timestamp=datetime(2026, 1, 11))
    b3 = BillingRecord(partner_id="p1", client_id="c1", operation="OP3", tokens_used=200, cost_usd=0.2, model_id="claude-3", timestamp=datetime(2026, 1, 12))
    
    db_session.add_all([b1, b2, b3])
    await db_session.commit()

    service = PartnerBillingService(db_session, partner_id="p1")
    by_model = await service.get_consumption_by_model(year=2026, month=1)

    assert len(by_model) == 2
    gpt4 = next(x for x in by_model if x["model_id"] == "gpt-4")
    assert gpt4["tokens"] == 150

@pytest.mark.asyncio
async def test_consumption_trend(db_session):
    """Tendencia ultimos meses."""
    # Data for multiple months
    # Assuming current test time is beyond Jan 2026, or we fake 'now' inside service. 
    # But service uses utcnow(). Ideally we mock datetime, but for simplicity we rely on service logic 
    # to query past months relative to 'now'.
    # Let's insert data for "last month" and "this month" relative to real time, 
    # OR better: The service takes 'months=6' and computes back from NOW.
    # So we need to insert data relative to datetime.utcnow()
    
    now = datetime.utcnow()
    last_month = now - timedelta(days=30)
    
    b1 = BillingRecord(partner_id="p_trend", client_id="c1", operation="x", tokens_used=100, cost_usd=1, model_id="m", timestamp=now)
    b2 = BillingRecord(partner_id="p_trend", client_id="c1", operation="x", tokens_used=200, cost_usd=2, model_id="m", timestamp=last_month)
    
    db_session.add_all([b1, b2])
    await db_session.commit()
    
    service = PartnerBillingService(db_session, partner_id="p_trend")
    trend = await service.get_consumption_trend(months=2)
    
    assert len(trend) == 2
    # trend[0] is (months-1) ago, trend[-1] is current/last month processed
    assert trend[-1]["tokens"] >= 100 # Current month might include both if days < 30 diff matches month calc? 
    # Actually get_consumption_trend logic iterates months.
    
@pytest.mark.asyncio
async def test_export_csv(db_session):
    """Exportar datos de facturacion a CSV."""
    c1 = ClientAccount(client_id="c_csv", partner_id="p_csv", name="CSV Client", license_key="k")
    db_session.add(c1)
    b1 = BillingRecord(partner_id="p_csv", client_id="c_csv", operation="x", tokens_used=1000, cost_usd=5.0, model_id="m", timestamp=datetime(2026, 1, 1))
    db_session.add(b1)
    await db_session.commit()
    
    service = PartnerBillingService(db_session, partner_id="p_csv")
    csv_out = await service.export_to_csv(year=2026, month=1)
    
    assert "client_id,client_name,tokens,cost_usd" in csv_out
    assert "c_csv,CSV Client,1000,5.0" in csv_out

@pytest.mark.asyncio
async def test_high_consumption_alert(db_session):
    """Detectar consumo inusualmente alto."""
    # 3 months average = 100
    # Current month = 200 (200%)
    now = datetime.utcnow()
    p = "p_alert"
    c = "c_alert"
    
    # Historic data (90 days ago)
    for i in range(3):
        ts = now - timedelta(days=30 * (i+1))
        b = BillingRecord(partner_id=p, client_id=c, operation="x", tokens_used=100, cost_usd=1, model_id="m", timestamp=ts)
        db_session.add(b)
        
    # Current month
    b_curr = BillingRecord(partner_id=p, client_id=c, operation="x", tokens_used=300, cost_usd=3, model_id="m", timestamp=now)
    db_session.add(b_curr)
    
    client = ClientAccount(client_id=c, partner_id=p, name="Alert Client", license_key="k")
    db_session.add(client)
    
    await db_session.commit()
    
    service = PartnerBillingService(db_session, partner_id=p)
    alerts = await service.get_high_consumption_alerts(threshold_percent=150)
    
    assert len(alerts) > 0
    assert alerts[0]["client_id"] == c
    assert alerts[0]["percent_increase"] > 0
