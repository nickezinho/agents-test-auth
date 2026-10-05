import pytest
from httpx import AsyncClient


def extract_cookie_value(response, cookie_name: str) -> str:
    """Auxiliar para extrair o valor do cookie do header Set-Cookie."""
    set_cookie = response.headers.get("set-cookie", "")
    for part in set_cookie.split(";"):
        if f"{cookie_name}=" in part:
            return part.split(f"{cookie_name}=")[1].strip()
    return ""


@pytest.mark.asyncio
async def test_refresh_token_rotation(async_client: AsyncClient):
    # 1. Cadastro e Login inicial
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotation@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Rotation User"
        }
    )
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "rotation@exemplo.com", "password": "SenhaForte@2026"}
    )
    assert login_res.status_code == 200
    token1 = login_res.json()["access_token"]
    cookie1 = extract_cookie_value(login_res, "refresh_token")
    assert cookie1 != ""

    # 2. Executa Rotação (Silent Refresh)
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": cookie1}
    )
    assert refresh_res.status_code == 200
    token2 = refresh_res.json()["access_token"]
    cookie2 = extract_cookie_value(refresh_res, "refresh_token")

    # Garante que um novo par de tokens foi gerado
    assert token2 != token1
    assert cookie2 != cookie1
    assert cookie2 != ""

    # 3. Testa acesso a rota protegida com o novo access token
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert me_res.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_reuse_attack_revokes_entire_family(async_client: AsyncClient):
    # 1. Login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "victim@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Victim User"
        }
    )
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "victim@exemplo.com", "password": "SenhaForte@2026"}
    )
    cookie1_original = extract_cookie_value(login_res, "refresh_token")

    # 2. Usuário legítimo faz refresh legal (gera cookie2 e consome cookie1)
    refresh1_res = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": cookie1_original}
    )
    assert refresh1_res.status_code == 200
    cookie2_legitimate = extract_cookie_value(refresh1_res, "refresh_token")

    # 3. ATAQUE DE REUSO / REPLAY: Atacante tenta usar o cookie1 antigo que já foi consumido!
    attacker_res = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": cookie1_original}
    )
    # Backend deve rejeitar e acionar alerta de segurança
    assert attacker_res.status_code == 401
    assert "violação de integridade" in attacker_res.json()["detail"].lower() or "revogado" in attacker_res.json()["detail"].lower()

    # 4. CONSEQUÊNCIA: O cookie2 legítimo também deve ter sido invalidado (família revogada)!
    victim_second_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": cookie2_legitimate}
    )
    # Acesso do usuário legítimo também é interrompido para proteção da conta
    assert victim_second_refresh.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_token_and_clears_cookie(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@exemplo.com",
            "password": "SenhaForte@2026",
            "full_name": "Logout User"
        }
    )
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "logout@exemplo.com", "password": "SenhaForte@2026"}
    )
    cookie = extract_cookie_value(login_res, "refresh_token")

    # Executa logout
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": cookie}
    )
    assert logout_res.status_code == 200
    assert "set-cookie" in logout_res.headers
    # Deve conter max-age=0 ou expires no passado
    set_cookie_header = logout_res.headers["set-cookie"]
    assert "max-age=0" in set_cookie_header.lower() or "expires=" in set_cookie_header.lower()

    # Tentativa subsequente de refresh com o token revogado deve falhar
    refresh_after_logout = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": cookie}
    )
    assert refresh_after_logout.status_code == 401
