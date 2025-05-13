# app/api/deps.py
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.database import AsyncSessionLocal  # se realmente precisar da factory
from app.models.usuario import Usuario # Corrected: Models are in app.models.py
from app.crud import crud_usuario # This should point to the instance in crud_usuario.py
from app.schemas.token_schemas import TokenData # Corrected: Import TokenData from token_schemas.py

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token" # Corrected tokenUrl to match auth endpoint
)

def get_db() -> Generator:
    try:
        db = AsyncSessionLocal()
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
        # Ensure that the payload keys match what TokenData expects (e.g., 'email' or 'sub')
        # The TokenData schema expects 'email'. The token is created with 'sub'.
        # Let's assume 'sub' in payload is the email for TokenData.
        email_from_payload = payload.get("sub")
        if email_from_payload is None:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials (sub is None in token)",
            )
        token_data = TokenData(email=email_from_payload)

    except (jwt.JWTError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials (JWTError or ValidationError)",
        )
    
    # token_data.sub was used before, but TokenData has 'email'. 
    # Assuming token_data.email is the correct field after instantiation.
    user = crud_usuario.get_by_email(db, email=token_data.email) 
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    if not crud_usuario.is_active(current_user): # crud_usuario is an instance of CRUDUsuario
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def get_current_active_superuser(
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    if not crud_usuario.is_superuser(current_user): # crud_usuario is an instance of CRUDUsuario
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn\"t have enough privileges"
        )
    return current_user

