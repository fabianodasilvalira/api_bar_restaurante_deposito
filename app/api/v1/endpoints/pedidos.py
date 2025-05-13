# app/api/v1/endpoints/pedidos.py
import uuid
from typing import List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.schemas.pedido_schemas import StatusPedido, PedidoSchemas  # Importar o Enum

from app.models.usuario import Usuario
from app.schemas import ItemPedido

from app.schemas.pedido_schemas import PedidoCreateSchemas

# from app.services.redis_service import redis_client, get_redis_client # Para publicar eventos no Redis
# import json # Para formatar mensagens Redis
# from app.services.pedido_service import update_pedido_status_and_notify # Serviço para encapsular lógica

router = APIRouter()

@router.post("/", response_model=PedidoSchemas, status_code=status.HTTP_201_CREATED)
def create_pedido(
    *,
    db: Session = Depends(deps.get_db),
    pedido_in: PedidoCreateSchemas,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Cria um novo pedido com seus itens.
    O pedido é associado a uma comanda existente.
    """
    try:
        # O id_usuario_registrou é o usuário logado que está fazendo a ação
        pedido = crud.crud_pedido.create(db=db, obj_in=pedido_in, id_usuario_registrou=current_user.id)

        # Publicar evento no Redis sobre o novo pedido (a lógica de publish está comentada no CRUD por enquanto)
        # comanda_db = crud.comanda.get(db, id=pedido.id_comanda)
        # redis_msg = {
        #     "evento": "novo_pedido",
        #     "pedido_id": str(pedido.id),
        #     "id_comanda": str(pedido.id_comanda),
        #     "id_mesa": str(comanda_db.id_mesa) if comanda_db else None,
        #     "itens_count": len(pedido.itens),
        #     "timestamp": pedido.data_criacao.isoformat()
        # }
        # await redis_client.publish_message(channel="pedidos_novos", message=json.dumps(redis_msg))
        # # Notificar cozinha/bar
        # await redis_client.publish_message(channel="cozinha_pedidos", message=json.dumps(redis_msg))

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return pedido

@router.get("/", response_model=List[PedidoSchemas])
def read_pedidos(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    id_comanda: Optional[uuid.UUID] = None,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera a lista de pedidos, opcionalmente filtrada por comanda.
    """
    if id_comanda:
        pedidos = crud.crud_pedido.get_multi_by_comanda(db, comanda_id=id_comanda, skip=skip, limit=limit)
    else:
        # Implementar crud.pedido.get_multi(db, skip=skip, limit=limit) se necessário listar todos os pedidos
        # Por ora, vamos focar em pedidos por comanda.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID da comanda é obrigatório para listar pedidos por enquanto.")
    return pedidos

@router.get("/{pedido_id}", response_model=PedidoSchemas)
def read_pedido_by_id(
    pedido_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera um pedido pelo seu ID.
    """
    pedido = crud.crud_pedido.get(db=db, id=pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return pedido

@router.put("/{pedido_id}/status", response_model=PedidoSchemas)
async def update_pedido_status(
    *,
    db: Session = Depends(deps.get_db),
    # redis: aioredis.Redis = Depends(get_redis_client), # Se for injetar o cliente redis
    pedido_id: uuid.UUID,
    novo_status: StatusPedido, # Receber o novo status como query parameter ou no corpo
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Atualiza o status geral de um pedido e seus itens (se aplicável).
    Publica a atualização no Redis.
    """
    pedido = crud.crud_pedido.get(db=db, id=pedido_id)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    # Usar o serviço que encapsula a lógica de atualização e notificação
    # updated_pedido, error_message = await update_pedido_status_and_notify(
    #     db=db, pedido_id=pedido_id, status_novo=novo_status, current_user=current_user
    # )
    # A função update_pedido_status_and_notify precisa ser ajustada para não cometer o db dentro dela se o crud_pedido já faz.
    # Por agora, chamaremos o CRUD diretamente e a lógica de Redis está comentada no CRUD.

    updated_pedido = crud.crud_pedido.update_status_geral(db=db, pedido_id=pedido_id, novo_status=novo_status)
    if not updated_pedido:
        # Isso não deveria acontecer se o pedido foi encontrado acima, a menos que update_status_geral retorne None em erro
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar status do pedido.")

    # A lógica de publicação no Redis está comentada dentro do crud_pedido.update_status_geral
    # Se for movida para cá ou para um serviço, seria chamada aqui.
    # Exemplo:
    # comanda_db = crud.comanda.get(db, id=updated_pedido.id_comanda)
    # redis_msg = {
    #     "evento": "status_pedido_atualizado",
    #     "pedido_id": str(updated_pedido.id),
    #     "novo_status_geral": novo_status.value,
    #     "id_comanda": str(updated_pedido.id_comanda),
    #     "id_mesa": str(comanda_db.id_mesa) if comanda_db else None,
    #     "timestamp": datetime.utcnow().isoformat() # Precisa importar datetime
    # }
    # await redis_client.publish_message(channel="pedidos_status_updates", message=json.dumps(redis_msg))
    # await redis_client.publish_message(channel=f"comanda_{updated_pedido.id_comanda}_updates", message=json.dumps(redis_msg))

    return updated_pedido


@router.put("/itens/{item_pedido_id}/status", response_model=ItemPedido)
async def update_item_pedido_status(
    *,
    db: Session = Depends(deps.get_db),
    item_pedido_id: uuid.UUID,
    novo_status: StatusPedido,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Atualiza o status de um item de pedido específico.
    Publica a atualização no Redis.
    """
    item_pedido = crud.crud_item_pedido.get(db=db, id=item_pedido_id)
    if not item_pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item do pedido não encontrado")

    updated_item = crud.crud_item_pedido.update_status(db=db, item_pedido_id=item_pedido_id, novo_status=novo_status)
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar status do item do pedido.")

    # A lógica de publicação no Redis está comentada dentro do crud_item_pedido.update_status
    # Exemplo:
    # comanda_db = crud.comanda.get(db, id=updated_item.id_comanda)
    # redis_msg = {
    #     "evento": "status_item_pedido_atualizado",
    #     "item_pedido_id": str(updated_item.id),
    #     "pedido_id": str(updated_item.id_pedido),
    #     "novo_status_item": novo_status.value,
    #     "id_comanda": str(updated_item.id_comanda),
    #     "id_mesa": str(comanda_db.id_mesa) if comanda_db else None,
    #     "timestamp": datetime.utcnow().isoformat()
    # }
    # await redis_client.publish_message(channel="pedidos_status_updates", message=json.dumps(redis_msg))
    # await redis_client.publish_message(channel=f"comanda_{updated_item.id_comanda}_updates", message=json.dumps(redis_msg))

    # Após atualizar um item, pode ser necessário reavaliar o status_geral_pedido do Pedido pai.
    # Ex: se todos os itens estão "Pronto para Entrega", o pedido geral pode mudar para "Pronto para Entrega".
    # Esta lógica pode ficar no CRUD ou em um serviço.

    return updated_item

# Cancelar um pedido ou item de pedido (geralmente mudar status para CANCELADO)
# A remoção física de itens/pedidos após o processamento inicial geralmente não é recomendada.

