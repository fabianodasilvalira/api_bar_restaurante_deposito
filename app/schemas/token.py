# app/schemas/token.py
from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[EmailStr] = None # Alterado para EmailStr para refletir o uso de email

# Reconfirmando a necessidade de TokenData, pois TokenPayload parece mais adequado para o JWT.
# Se TokenData for usado para validar o payload decodificado, ele deve corresponder ao que está no JWT.
# No deps.py, TokenData(email=email) foi usado. Vamos alinhar.
class TokenData(BaseModel):
    email: Optional[str] = None

