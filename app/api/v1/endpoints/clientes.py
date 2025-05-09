from asyncio.log import logger
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.auth import AuthService
from app.crud import crud_cliente as crud_cliente
from app.database import get_db
from app.models import Usuario as DBUsuario, Cliente as DBCliente

router = APIRouter()

@router.post("/", response_model=schemas.ClienteSchemas, status_code=status.HTTP_201_CREATED)
async def create_cliente(
    cliente_in: schemas.ClienteCreateSchemas,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.ClienteSchemas:
    """
    Cria um novo cliente.
    Requer autenticação.
    """
    try:
        # Verifica se já existe cliente com o mesmo telefone
        if cliente_in.telefone:
            existing_cliente = crud_cliente.get_by_telefone(db, telefone=cliente_in.telefone)
            if existing_cliente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe um cliente com o telefone {cliente_in.telefone}"
                )

        cliente = crud_cliente.create(db=db, obj_in=cliente_in)
        logger.info(f"Cliente {cliente.id} criado por {current_user.email}")
        return cliente

    except Exception as e:
        logger.error(f"Erro ao criar cliente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar cliente"
        )

@router.get("/", response_model=List[schemas.ClienteSchemas])
async def read_clientes(
    skip: int = 0,
    limit: int = 100,
    telefone: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.ClienteSchemas]:
    """
    Lista clientes com paginação.
    Filtro opcional por telefone.
    """
    try:
        if telefone:
            cliente = crud_cliente.get_by_telefone(db, telefone=telefone)
            return [cliente] if cliente else []
        return crud_cliente.get_multi(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar clientes"
        )

@router.get("/{cliente_id}", response_model=schemas.ClienteSchemas)
async def read_cliente(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.ClienteSchemas:
    """
    Obtém um cliente específico pelo ID.
    """
    cliente = crud_cliente.get(db, id=cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente

@router.put("/{cliente_id}", response_model=schemas.ClienteSchemas)
async def update_cliente(
    cliente_id: uuid.UUID,
    cliente_in: schemas.ClienteUpdateSchemas,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.ClienteSchemas:
    """
    Atualiza os dados de um cliente.
    """
    try:
        db_cliente = crud_cliente.get(db, id=cliente_id)
        if not db_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        # Verifica se o novo telefone já existe
        if cliente_in.telefone and cliente_in.telefone != db_cliente.telefone:
            existing = crud_cliente.get_by_telefone(db, telefone=cliente_in.telefone)
            if existing and existing.id != cliente_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telefone já cadastrado para outro cliente"
                )

        updated_cliente = crud_cliente.update(db, db_obj=db_cliente, obj_in=cliente_in)
        logger.info(f"Cliente {cliente_id} atualizado por {current_user.email}")
        return updated_cliente

    except Exception as e:
        logger.error(f"Erro ao atualizar cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar cliente"
        )

@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cliente(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> None:
    """
    Remove um cliente (apenas administradores).
    Verifica se não há fiados pendentes antes de deletar.
    """
    try:
        db_cliente = crud_cliente.get(db, id=cliente_id)
        if not db_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        # Verifica fiados pendentes (implementar no CRUD)
        if crud_cliente.has_fiados_pendentes(db, cliente_id=cliente_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível remover cliente com fiados pendentes"
            )

        crud_cliente.remove(db, id=cliente_id)
        logger.info(f"Cliente {cliente_id} removido por {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao remover cliente"
        )