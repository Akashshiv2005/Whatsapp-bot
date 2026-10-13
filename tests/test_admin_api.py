import pytest
from httpx import AsyncClient
from app.models import Service, Lead


@pytest.mark.asyncio
async def test_admin_api_auth_required(client: AsyncClient):
    # Missing API key
    response = await client.get("/api/v1/services")
    assert response.status_code == 401

    # Invalid API key
    response = await client.get("/api/v1/services", headers={"X-Admin-API-Key": "wrong_key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_services_crud(client: AsyncClient, db_session):
    headers = {"X-Admin-API-Key": "test_admin_secret_key"}

    # 1. Create service
    payload = {
        "name": "Custom ERP",
        "slug": "custom-erp",
        "description": "Enterprise ERP solution",
        "category": "Software Development",
        "active": True,
        "sort_order": 10
    }
    create_res = await client.post("/api/v1/services", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. Get service
    get_res = await client.get(f"/api/v1/services/{created_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["slug"] == "custom-erp"

    # 3. Update service
    update_res = await client.put(
        f"/api/v1/services/{created_id}",
        json={"name": "Custom ERP NextGen"},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Custom ERP NextGen"

    # 4. List services
    list_res = await client.get("/api/v1/services", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_admin_lead_status_update(client: AsyncClient, db_session):
    headers = {"X-Admin-API-Key": "test_admin_secret_key"}

    # Seed lead
    lead = Lead(
        name="John Doe",
        phone_number="919876543210",
        email="john@example.com",
        business_type="Retail",
        requirement="POS System",
        budget="₹25,000 – ₹50,000",
        status="NEW"
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    # Patch status to QUALIFIED
    patch_res = await client.patch(
        f"/api/v1/leads/{lead.id}",
        json={"status": "QUALIFIED"},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "QUALIFIED"


@pytest.mark.asyncio
async def test_admin_analytics_summary(client: AsyncClient, db_session):
    headers = {"X-Admin-API-Key": "test_admin_secret_key"}
    res = await client.get("/api/v1/analytics/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "conversations" in data
    assert "leads" in data
    assert "messages" in data
