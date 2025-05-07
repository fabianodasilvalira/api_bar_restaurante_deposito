# app/schemas/token.py
from typing import Optional
import uuid

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[uuid.UUID] = None # Alterado para UUID se o ID do usuário for UUID
    # Se "sub" for o email, mantenha como Optional[str]
    # Para este projeto, o "sub" no JWT será o email do usuário.
    # sub: Optional[str] = None

# Reconfirmando a necessidade de TokenData, pois TokenPayload parece mais adequado para o JWT.
# Se TokenData for usado para validar o payload decodificado, ele deve corresponder ao que está no JWT.
# No deps.py, TokenData(email=email) foi usado. Vamos alinhar.
class TokenData(BaseModel):
    email: Optional[str] = None

