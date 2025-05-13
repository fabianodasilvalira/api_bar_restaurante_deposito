# app/api/v1/endpoints/auth.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.usuario import Usuario as DBUsuario
from app.schemas.usuario_schemas import UsuarioCreateSchemas, UsuarioUpdateSchemas, UsuarioSchemas, UsuarioInDBBaseSchemas, UsuarioBaseSchemas

router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await crud.usuario.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ou senha incorretos")
    elif not crud.usuario.is_active(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.email, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login/test-token", response_model=UsuarioSchemas)
async def test_token(current_user: DBUsuario = Depends(deps.get_current_user)) -> Any:
    """
    Test access token.
    """
    return current_user


@router.post("/users/open", response_model=UsuarioSchemas, status_code=status.HTTP_201_CREATED)
async def create_user_open(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UsuarioCreateSchemas
) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = await crud.usuario.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user_in.is_superuser = False
    user = await crud.usuario.create(db, obj_in=user_in)
    return user


@router.get("/users/me", response_model=UsuarioSchemas)
async def read_user_me(
    db: AsyncSession = Depends(deps.get_db),
    current_user: DBUsuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get current user.
    """
    return current_user
