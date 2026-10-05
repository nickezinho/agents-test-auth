import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_protected_dashboard_with_valid_token(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "dash@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Dashboard Tester"
        }
    )
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "dash@exemplo.com", "password": "SenhaForte@2026"}
    )
    token = login_res.json()["access_token"]

    response = await async_client.get(
        "/api/v1/protected/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "metrics" in data
    assert "session_info" in data
    assert data["session_info"]["email"] == "dash@exemplo.com"


@pytest.mark.asyncio
async def test_protected_dashboard_without_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/protected/dashboard")
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_protected_dashboard_tampered_token(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/protected/dashboard",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.adulterado.assinaturainvalida"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
