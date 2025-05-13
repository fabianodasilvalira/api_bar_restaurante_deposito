# app/api/v1/endpoints/clientes.py
from typing import List, Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.models.usuario import Usuario

router = APIRouter()

@router.post("/", response_model=schemas.Cliente, status_code=status.HTTP_201_CREATED)
def create_cliente(
    *,
    db: Session = Depends(deps.get_db),
    cliente_in: schemas.ClienteCreate,
    current_user:Usuario = Depends(deps.get_current_active_user) # Apenas usuários logados podem criar clientes
) -> Any:
    """
    Cria um novo cliente.
    """
    # Verificar se já existe cliente com o mesmo telefone, se for um campo único
    if cliente_in.telefone:
        existing_cliente = crud.cliente.get_by_telefone(db, telefone=cliente_in.telefone)
        if existing_cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cliente com o telefone {cliente_in.telefone} já existe."
            )
    cliente = crud.cliente.create(db=db, obj_in=cliente_in)
    return cliente

@router.get("/", response_model=List[schemas.Cliente])
def read_clientes(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user:Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera a lista de clientes.
    """
    clientes = crud.cliente.get_multi(db, skip=skip, limit=limit)
    return clientes

@router.get("/{cliente_id}", response_model=schemas.Cliente)
def read_cliente_by_id(
    cliente_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user:Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera um cliente pelo seu ID.
    """
    cliente = crud.cliente.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return cliente

@router.put("/{cliente_id}", response_model=schemas.Cliente)
def update_cliente(
    *,
    db: Session = Depends(deps.get_db),
    cliente_id: uuid.UUID,
    cliente_in: schemas.ClienteUpdate,
    current_user:Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Atualiza um cliente.
    """
    cliente = crud.cliente.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    # Se o telefone está sendo atualizado, verificar se o novo telefone já existe para outro cliente
    if cliente_in.telefone and cliente_in.telefone != cliente.telefone:
        existing_cliente = crud.cliente.get_by_telefone(db, telefone=cliente_in.telefone)
        if existing_cliente and existing_cliente.id != cliente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Outro cliente com o telefone {cliente_in.telefone} já existe."
            )

    cliente = crud.cliente.update(db=db, db_obj=cliente, obj_in=cliente_in)
    return cliente

@router.delete("/{cliente_id}", response_model=schemas.Cliente)
def delete_cliente(
    *,
    db: Session = Depends(deps.get_db),
    cliente_id: uuid.UUID,
    current_user:Usuario = Depends(deps.get_current_active_superuser) # Apenas superusuários podem deletar clientes
) -> Any:
    """
    Deleta um cliente.
    Apenas superusuários podem realizar esta ação.
    Verificar regras de negócio (ex: fiados pendentes) no CRUD.
    """
    cliente = crud.cliente.get(db=db, id=cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    try:
        cliente_removido = crud.cliente.remove(db=db, id=cliente_id)
    except ValueError as e: # Captura o erro de fiado pendente do CRUD
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return cliente_removido

