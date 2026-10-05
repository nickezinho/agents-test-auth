import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "teste@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Usuário Teste"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "teste@exemplo.com"
    assert data["full_name"] == "Usuário Teste"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(async_client: AsyncClient):
    payload = {
        "email": "duplicado@exemplo.com",
        "password": "SenhaForte@2026",
        "full_name": "Usuário Original"
    }
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_password_policy_validation(async_client: AsyncClient):
    # Senha fraca (sem maiúscula, sem símbolo)
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "fraco@exemplo.com",
            "password": "senhafraca123",
            "full_name": "Usuário Fraco"
        }
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_success_and_cookie_emission(async_client: AsyncClient):
    # Primeiro registra
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Login User"
        }
    )

    # Executa login
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@exemplo.com",
            "password": "SenhaForte@2026"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "login@exemplo.com"

    # Checa emissão de cookie HttpOnly
    assert "set-cookie" in response.headers
    cookie_header = response.headers["set-cookie"]
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Wrong Pw User"
        }
    )

    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpw@exemplo.com",
            "password": "SenhaIncorreta@99"
        }
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_user_not_found(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "naoexiste@exemplo.com",
            "password": "QualquerSenha@123"
        }
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_google_auth_new_user(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/google",
        json={"id_token": "mock_google_token_:google_user@exemplo.com:Google Person:sub_goog_999"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "google_user@exemplo.com"
    assert data["user"]["full_name"] == "Google Person"
    assert data["user"]["is_oauth_only"] is True


@pytest.mark.asyncio
async def test_google_auth_existing_user_account_linking(async_client: AsyncClient):
    # Registra localmente primeiro
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "linking@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Conta Local"
        }
    )

    # Entra via Google com o mesmo e-mail
    response = await async_client.post(
        "/api/v1/auth/google",
        json={"id_token": "mock_google_token_:linking@exemplo.com:Conta Google:sub_goog_linking"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "linking@exemplo.com"


@pytest.mark.asyncio
async def test_get_current_user_me(async_client: AsyncClient):
    # Registra e loga
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Me User"
        }
    )
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "me@exemplo.com", "password": "SenhaForte@2026"}
    )
    token = login_res.json()["access_token"]

    # Consulta /me com Bearer
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "me@exemplo.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized_without_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
