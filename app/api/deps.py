# app/api/deps.py
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.database import SessionLocal
from app.db.models.usuario import Usuario # Ajuste o caminho se necessário
from app.crud import crud_usuario # Ajuste o caminho se necessário
from app.schemas.token import TokenDataSchemas # Ajuste o caminho se necessário

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> Usuario:
    try:
        payload = security.decode_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials (payload is None)",
            )
        token_data = TokenDataSchemas(**payload)
    except (jwt.JWTError, ValidationError) as e:
        # Log a exceção e:
        # print(f"Token decoding/validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials (JWTError or ValidationError)",
        )
    
    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials (sub is None)",
        )

    user = crud_usuario.usuario.get_by_email(db, email=token_data.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    if not crud_usuario.usuario.is_active(current_user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def get_current_active_superuser(
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    if not crud_usuario.usuario.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn\'t have enough privileges"
        )
    return current_user

