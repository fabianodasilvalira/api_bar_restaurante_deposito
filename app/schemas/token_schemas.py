from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None  # ou: str | None (Python 3.10+)

class TokenData(BaseModel):  # <--- esta classe pode estar faltando
    username: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str
