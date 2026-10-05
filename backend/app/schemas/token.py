import uuid
from typing import Optional
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    iat: int
    exp: int
    jti: str
    token_type: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
