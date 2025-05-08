from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.schemas import ItemPedidoCreate, ItemPedidoUpdate, ItemPedido as ItemPedidoSchema
from app.models import ItemPedido as DBItemPedido, Pedido as DBPedido
from app.crud import item_pedido as crud_item_pedido
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.services.pedido_service import PedidoService

router = APIRouter()


@router.post("/", response_model=ItemPedidoSchema, status_code=status.HTTP_201_CREATED)
async def create_item_pedido(
        pedido_id: uuid.UUID,
        item: ItemPedidoCreate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Adiciona um novo item a um pedido existente
    """
    pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Verifica se o pedido pode ser modificado
    if pedido.status in ["Cancelado", "Entregue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível adicionar itens a pedidos cancelados ou entregues"
        )

    # Usa o serviço para adicionar o item
    item_pedido, message = await PedidoService().adicionar_item_pedido(
        db=db,
        pedido_id=pedido_id,
        item_in=item,
        current_user=current_user
    )

    if not item_pedido:
        raise HTTPException(status_code=400, detail=message)

    return item_pedido


@router.get("/", response_model=List[ItemPedidoSchema])
async def read_itens_pedido(
        pedido_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Lista todos os itens de um pedido específico
    """
    pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Verifica se o usuário tem acesso a este pedido
    if current_user.cargo not in ["admin", "gerente"] and pedido.id_usuario_solicitante != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este pedido")

    return crud_item_pedido.get_by_pedido(db, pedido_id=pedido_id, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ItemPedidoSchema)
async def read_item_pedido(
        pedido_id: uuid.UUID,
        item_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Obtém um item específico de um pedido
    """
    db_item = crud_item_pedido.get(db, id=item_id)
    if not db_item or db_item.id_pedido != pedido_id:
        raise HTTPException(status_code=404, detail="Item não encontrado neste pedido")

    # Verifica permissões
    pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    if current_user.cargo not in ["admin", "gerente"] and pedido.id_usuario_solicitante != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este item")

    return db_item


@router.put("/{item_id}", response_model=ItemPedidoSchema)
async def update_item_pedido(
        pedido_id: uuid.UUID,
        item_id: uuid.UUID,
        item: ItemPedidoUpdate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Atualiza um item de pedido existente
    """
    db_item = crud_item_pedido.get(db, id=item_id)
    if not db_item or db_item.id_pedido != pedido_id:
        raise HTTPException(status_code=404, detail="Item não encontrado neste pedido")

    # Verifica se o pedido pode ser modificado
    pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    if pedido.status in ["Cancelado", "Entregue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível modificar itens de pedidos cancelados ou entregues"
        )

    # Verifica permissões
    if current_user.cargo not in ["admin", "gerente"] and pedido.id_usuario_solicitante != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para atualizar este item")

    return crud_item_pedido.update(db, db_obj=db_item, obj_in=item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_pedido(
        pedido_id: uuid.UUID,
        item_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
):
    """
    Remove um item de um pedido
    """
    db_item = crud_item_pedido.get(db, id=item_id)
    if not db_item or db_item.id_pedido != pedido_id:
        raise HTTPException(status_code=404, detail="Item não encontrado neste pedido")

    # Verifica se o pedido pode ser modificado
    pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    if pedido.status in ["Cancelado", "Entregue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover itens de pedidos cancelados ou entregues"
        )

    # Verifica permissões
    if current_user.cargo not in ["admin", "gerente"] and pedido.id_usuario_solicitante != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para remover este item")

    crud_item_pedido.remove(db, id=item_id)
    return None