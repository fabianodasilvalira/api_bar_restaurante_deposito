from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas import UsuarioCreate, UsuarioUpdate, Usuario as UsuarioSchema
from app.models import Usuario as DBUsuario
from app.crud import usuario as crud_usuario
from app.db.database import get_db
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/", response_model=UsuarioSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
        usuario: UsuarioCreate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
):
    """
    Cria um novo usuário (apenas administradores)
    """
    db_user = crud_usuario.get_by_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    return crud_usuario.create(db, obj_in=usuario)


@router.get("/", response_model=List[UsuarioSchema])
async def read_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
):
    """
    Lista todos os usuários (apenas administradores)
    """
    return crud_usuario.get_multi(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UsuarioSchema)
async def read_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Obtém um usuário específico (próprio usuário ou admin)
    """
    db_user = crud_usuario.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Usuário só pode ver seu próprio perfil, a menos que seja admin
    if current_user.cargo != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este recurso")

    return db_user


@router.put("/{user_id}", response_model=UsuarioSchema)
async def update_user(
        user_id: int,
        usuario: UsuarioUpdate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Atualiza um usuário (próprio usuário ou admin)
    """
    db_user = crud_usuario.get(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Verifica permissões
    if current_user.cargo != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão para atualizar este usuário")

    return crud_usuario.update(db, db_obj=db_user, obj_in=usuario)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
):
    """
    Remove um usuário (apenas administradores)
    """
    db_user = crud_usuario.get(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Impede que um admin se delete
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio usuário")

    crud_usuario.remove(db, id=user_id)
    return None