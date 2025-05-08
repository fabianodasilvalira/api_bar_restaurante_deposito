from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.crud import usuario as crud_usuario
from app.db.database import get_db
from app.models import Usuario as DBUsuario
from app.services.auth_service import AuthService
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
        db: Session = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 token login (email + password).
    Returns access and refresh tokens.
    """
    try:
        # Usa o AuthService para autenticação
        token = await AuthService().login_for_access_token(
            db=db,
            form_data=form_data
        )
        logger.info(f"Login bem-sucedido para usuário: {form_data.username}")
        return token
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar login"
        )


@router.post("/refresh-token", response_model=schemas.Token)
async def refresh_access_token(
        db: Session = Depends(get_db),
        refresh_token: str
) -> Any:
    """
    Refresh an expired access token using a valid refresh token.
    """
    try:
        token = await AuthService().refresh_access_token(
            db=db,
            refresh_token=refresh_token
        )
        return token
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao renovar token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao renovar token"
        )


@router.get("/me", response_model=schemas.Usuario)
async def read_user_me(
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> Any:
    """
    Get current logged-in user data.
    """
    return current_user


@router.post("/register", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED)
async def register_new_user(
        user_in: schemas.UsuarioCreate,
        db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user (open endpoint).
    By default, new users are not admins and are active.
    """
    try:
        # Verifica se o email já existe
        if crud_usuario.get_by_email(db, email=user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registrado no sistema"
            )

        # Cria o usuário com cargo padrão 'garcom' se não especificado
        if not user_in.cargo:
            user_in.cargo = "garcom"

        user_in.ativo = True  # Ativa por padrão
        user_in.hashed_password = AuthService.get_password_hash(user_in.password)

        db_user = crud_usuario.create(db, obj_in=user_in)
        logger.info(f"Novo usuário registrado: {db_user.email}")
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no registro de usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao registrar usuário"
        )