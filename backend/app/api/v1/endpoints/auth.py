from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthSuccessResponse,
    GoogleAuthRequest,
    LoginRequest,
    LogoutResponse,
)
from app.schemas.token import TokenRefreshResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.google_oauth import GoogleOAuthService
from app.services.token_service import TokenService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    """Configura o cookie HttpOnly de Refresh Token com todos os atributos de segurança."""
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        path=settings.COOKIE_PATH,
        domain=None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE
    )


def clear_refresh_token_cookie(response: Response) -> None:
    """Invalida o cookie de Refresh Token no navegador."""
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastro de novo usuário com e-mail e senha"
)
async def register(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    new_user = await AuthService.register_user(db, user_in, ip_address=ip, user_agent=ua)
    return new_user


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login com e-mail e senha"
)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = get_user_agent(request)

    user = await AuthService.authenticate_local(db, login_data, ip_address=ip, user_agent=ua)
    access_token, refresh_token = await TokenService.create_session_tokens(
        db, user, ip_address=ip, user_agent=ua
    )

    set_refresh_token_cookie(response, refresh_token)

    return AuthSuccessResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/google",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login ou Cadastro federado via Google Identity Services"
)
async def google_auth(
    google_in: GoogleAuthRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = get_user_agent(request)

    google_payload = GoogleOAuthService.verify_id_token(google_in.id_token)
    user = await AuthService.authenticate_or_register_google(
        db, google_payload, ip_address=ip, user_agent=ua
    )

    access_token, refresh_token = await TokenService.create_session_tokens(
        db, user, ip_address=ip, user_agent=ua
    )

    set_refresh_token_cookie(response, refresh_token)

    return AuthSuccessResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotação de Refresh Token e renovação silenciosa"
)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = get_user_agent(request)

    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    new_access_token, new_refresh_token = await TokenService.rotate_refresh_token(
        db, raw_token, ip_address=ip, user_agent=ua
    )

    set_refresh_token_cookie(response, new_refresh_token)

    return TokenRefreshResponse(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Encerramento de sessão e invalidação de refresh token"
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if raw_token:
        await TokenService.revoke_refresh_token(db, raw_token)

    clear_refresh_token_cookie(response)
    return LogoutResponse(message="Sessão encerrada com sucesso.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Perfil do usuário autenticado no token atual"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
