import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import pedido as crud_pedido, comanda as crud_comanda, item_pedido as crud_item_pedido
from app.db.database import get_db
from app.models import Usuario as DBUsuario, Pedido as DBPedido, StatusPedido
from app.services.auth_service import AuthService
from app.services.redis_service import RedisService
from app.services.pedido_service import PedidoService
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=schemas.PedidoDetail, status_code=status.HTTP_201_CREATED)
async def create_pedido(
    pedido_in: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.PedidoDetail:
    """
    Cria um novo pedido com itens associados.
    Atualiza automaticamente o valor total da comanda.
    """
    try:
        # Verifica se a comanda existe e está aberta
        comanda = crud_comanda.get(db, id=pedido_in.id_comanda)
        if not comanda or comanda.status_pagamento in ["Totalmente Pago", "Fiado Fechado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda não encontrada ou já fechada"
            )

        # Usa o serviço para criar o pedido
        pedido, message = await PedidoService().create_pedido(
            db=db,
            pedido_in=pedido_in,
            usuario_id=current_user.id
        )

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"comanda_{pedido_in.id_comanda}_pedidos",
            message={
                "event": "novo_pedido",
                "pedido_id": str(pedido.id),
                "itens_count": len(pedido.itens_pedido),
                "responsavel": current_user.email
            }
        )

        # Publica para a cozinha/bar se houver itens relevantes
        if any(item.produto.categoria in ["COMIDA", "BEBIDA"] for item in pedido.itens_pedido):
            await RedisService().publish(
                channel="cozinha_pedidos",
                message={
                    "event": "novo_pedido_cozinha",
                    "pedido_id": str(pedido.id),
                    "comanda_id": str(pedido_in.id_comanda),
                    "itens_count": len([i for i in pedido.itens_pedido if i.produto.categoria in ["COMIDA", "BEBIDA"]])
                }
            )

        logger.info(f"Pedido {pedido.id} criado por {current_user.email}")
        return pedido

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar pedido"
        )

@router.get("/", response_model=List[schemas.Pedido])
async def list_pedidos(
    comanda_id: Optional[uuid.UUID] = None,
    status: Optional[StatusPedido] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.Pedido]:
    """
    Lista pedidos com filtros opcionais:
    - comanda_id: Filtra por comanda específica
    - status: Filtra por status do pedido
    """
    try:
        if comanda_id:
            # Verifica se o usuário tem acesso à comanda
            comanda = crud_comanda.get(db, id=comanda_id)
            if not comanda:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comanda não encontrada"
                )

            if current_user.cargo not in ["admin", "gerente"]:
                if comanda.mesa and comanda.mesa.id_usuario_responsavel != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Sem permissão para acessar esta comanda"
                    )

            return crud_pedido.get_by_comanda(
                db=db,
                comanda_id=comanda_id,
                status=status,
                skip=skip,
                limit=limit
            )
        else:
            # Somente admin/gerente pode listar todos os pedidos
            if current_user.cargo not in ["admin", "gerente"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Somente administradores podem listar todos os pedidos"
                )

            return crud_pedido.get_multi(
                db=db,
                status=status,
                skip=skip,
                limit=limit
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar pedidos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar pedidos"
        )

@router.get("/{pedido_id}", response_model=schemas.PedidoDetail)
async def get_pedido(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.PedidoDetail:
    """
    Obtém detalhes de um pedido específico, incluindo todos os itens.
    """
    try:
        pedido = crud_pedido.get(db, id=pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado"
            )

        # Verifica permissão
        if current_user.cargo not in ["admin", "gerente"]:
            if pedido.comanda.mesa and pedido.comanda.mesa.id_usuario_responsavel != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar este pedido"
                )

        return pedido

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter pedido {pedido_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter pedido"
        )

@router.put("/{pedido_id}/status", response_model=schemas.Pedido)
async def update_pedido_status(
    pedido_id: uuid.UUID,
    status_update: schemas.PedidoStatusUpdate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Pedido:
    """
    Atualiza o status geral de um pedido.
    Valida transições de status permitidas.
    """
    try:
        # Usa o serviço para atualizar o status
        pedido, message = await PedidoService().update_pedido_status(
            db=db,
            pedido_id=pedido_id,
            novo_status=status_update.status,
            usuario_id=current_user.id
        )

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"comanda_{pedido.id_comanda}_pedidos",
            message={
                "event": "status_pedido_atualizado",
                "pedido_id": str(pedido.id),
                "novo_status": pedido.status.value,
                "atualizado_por": current_user.email
            }
        )

        logger.info(f"Status do pedido {pedido_id} atualizado para {status_update.status} por {current_user.email}")
        return pedido

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status do pedido {pedido_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar status do pedido"
        )

@router.put("/itens/{item_id}/status", response_model=schemas.ItemPedido)
async def update_item_status(
    item_id: uuid.UUID,
    status_update: schemas.ItemPedidoStatusUpdate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.ItemPedido:
    """
    Atualiza o status de um item específico do pedido.
    Pode afetar o status geral do pedido.
    """
    try:
        # Usa o serviço para atualizar o item
        item, message = await PedidoService().update_item_status(
            db=db,
            item_id=item_id,
            novo_status=status_update.status,
            usuario_id=current_user.id
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"pedido_{item.id_pedido}_itens",
            message={
                "event": "status_item_atualizado",
                "item_id": str(item.id),
                "produto_id": str(item.id_produto),
                "novo_status": item.status.value,
                "atualizado_por": current_user.email
            }
        )

        logger.info(f"Status do item {item_id} atualizado para {status_update.status} por {current_user.email}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status do item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar status do item"
        )

@router.post("/{pedido_id}/cancelar", response_model=schemas.Pedido)
async def cancelar_pedido(
    pedido_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Pedido:
    """
    Cancela um pedido existente.
    Atualiza o valor total da comanda.
    """
    try:
        # Usa o serviço para cancelar o pedido
        pedido, message = await PedidoService().cancelar_pedido(
            db=db,
            pedido_id=pedido_id,
            usuario_id=current_user.id
        )

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"comanda_{pedido.id_comanda}_pedidos",
            message={
                "event": "pedido_cancelado",
                "pedido_id": str(pedido.id),
                "cancelado_por": current_user.email
            }
        )

        logger.info(f"Pedido {pedido_id} cancelado por {current_user.email}")
        return pedido

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar pedido {pedido_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao cancelar pedido"
        )