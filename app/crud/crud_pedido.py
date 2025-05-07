# app/crud/crud_pedido.py
import uuid
from typing import List, Optional, Union, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models.pedido import Pedido, ItemPedido, StatusPedido
from app.db.models.produto import Produto # Para buscar preço do produto
from app.db.models.comanda import Comanda # Para associar e recalcular comanda
from app.schemas.pedido import PedidoCreate, PedidoUpdate, ItemPedidoCreate, ItemPedidoUpdate
from app.crud.crud_comanda import comanda as crud_comanda # Para recalcular comanda
# from app.services.redis_service import redis_client # Para publicar eventos
# import json
# from datetime import datetime # Para timestamp em notificações Redis

class CRUDItemPedido:
    def get(self, db: Session, id: uuid.UUID) -> Optional[ItemPedido]:
        return db.query(ItemPedido).filter(ItemPedido.id == id).first()

    def get_multi_by_pedido(self, db: Session, *, pedido_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[ItemPedido]:
        return db.query(ItemPedido).filter(ItemPedido.id_pedido == pedido_id).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: ItemPedidoCreate, pedido_id: uuid.UUID, comanda_id: uuid.UUID) -> ItemPedido:
        produto = db.query(Produto).filter(Produto.id == obj_in.id_produto).first()
        if not produto:
            raise ValueError(f"Produto com ID {obj_in.id_produto} não encontrado.")
        if not produto.disponivel:
            raise ValueError(f"Produto 	\"{produto.nome}	\" não está disponível.")

        preco_unitario = produto.preco_unitario
        preco_total_item = preco_unitario * obj_in.quantidade

        db_item = ItemPedido(
            id_pedido=pedido_id,
            id_comanda=comanda_id,
            id_produto=obj_in.id_produto,
            quantidade=obj_in.quantidade,
            preco_unitario_no_momento=preco_unitario,
            preco_total_item=preco_total_item,
            observacoes_item=obj_in.observacoes_item,
            status_item_pedido=StatusPedido.RECEBIDO # Status inicial do item
        )
        db.add(db_item)
        # O commit será feito após todos os itens do pedido serem adicionados ou no final do CRUDPedido.create
        return db_item

    def update_status(self, db: Session, *, item_pedido_id: uuid.UUID, novo_status: StatusPedido) -> Optional[ItemPedido]:
        item = self.get(db, id=item_pedido_id)
        if not item:
            return None
        
        # Adicionar lógica de transição de status se necessário
        item.status_item_pedido = novo_status
        db.add(item)
        db.commit()
        db.refresh(item)

        # Publicar no Redis
        # redis_msg = {
        #     "pedido_id": str(item.id_pedido),
        #     "item_pedido_id": str(item.id),
        #     "novo_status": novo_status.value,
        #     "id_comanda": str(item.id_comanda),
        #     "timestamp": datetime.utcnow().isoformat()
        # }
        # await redis_client.publish_message(channel="pedidos_status_updates", message=json.dumps(redis_msg))
        return item

    def remove(self, db: Session, *, id: uuid.UUID) -> Optional[ItemPedido]:
        obj = db.query(ItemPedido).get(id)
        if obj:
            if obj.status_item_pedido not in [StatusPedido.RECEBIDO, StatusPedido.CANCELADO]:
                raise ValueError(f"Item do pedido não pode ser removido pois já está {obj.status_item_pedido.value}")
            db.delete(obj)
            # O commit será feito pelo CRUDPedido ou após recalcular a comanda
        return obj

class CRUDPedido:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Pedido]:
        return db.query(Pedido).filter(Pedido.id == id).first()

    def get_multi_by_comanda(self, db: Session, *, comanda_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Pedido]:
        return db.query(Pedido).filter(Pedido.id_comanda == comanda_id).order_by(Pedido.data_criacao.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: PedidoCreate, id_usuario_registrou: Optional[uuid.UUID]) -> Pedido:
        comanda = db.query(Comanda).filter(Comanda.id == obj_in.id_comanda).first()
        if not comanda:
            raise ValueError(f"Comanda com ID {obj_in.id_comanda} não encontrada.")
        if comanda.status_comanda not in [StatusComanda.ABERTA, StatusComanda.PAGA_PARCIALMENTE]:
            raise ValueError(f"Não é possível adicionar pedidos a uma comanda que não está Aberta ou Parcialmente Paga (status: {comanda.status_comanda.value}).")

        db_pedido = Pedido(
            id_comanda=obj_in.id_comanda,
            id_usuario_registrou=id_usuario_registrou,
            tipo_pedido=obj_in.tipo_pedido,
            observacoes_pedido=obj_in.observacoes_pedido,
            status_geral_pedido=StatusPedido.RECEBIDO # Status inicial do pedido geral
        )
        db.add(db_pedido)
        db.flush() # Para obter o ID do pedido para os itens

        itens_criados = []
        for item_in in obj_in.itens:
            try:
                item_criado = crud_item_pedido.create(db, obj_in=item_in, pedido_id=db_pedido.id, comanda_id=db_pedido.id_comanda)
                itens_criados.append(item_criado)
            except ValueError as e:
                db.rollback() # Desfaz a criação do pedido e itens anteriores se um item falhar
                raise ValueError(f"Erro ao criar item do pedido: {str(e)}")
        
        db_pedido.itens = itens_criados # Associa os itens criados ao pedido
        db.commit()
        db.refresh(db_pedido)

        # Recalcular totais da comanda após adicionar o pedido
        crud_comanda.recalcular_total_comanda(db, comanda_id=db_pedido.id_comanda)

        # Publicar no Redis
        # redis_msg = {
        #     "evento": "novo_pedido",
        #     "pedido_id": str(db_pedido.id),
        #     "id_comanda": str(db_pedido.id_comanda),
        #     "id_mesa": str(comanda.id_mesa) if comanda else None,
        #     "timestamp": datetime.utcnow().isoformat()
        # }
        # await redis_client.publish_message(channel="pedidos_novos", message=json.dumps(redis_msg))
        return db_pedido

    def update_status_geral(self, db: Session, *, pedido_id: uuid.UUID, novo_status: StatusPedido) -> Optional[Pedido]:
        pedido = self.get(db, id=pedido_id)
        if not pedido:
            return None
        
        # Adicionar lógica de transição de status se necessário
        pedido.status_geral_pedido = novo_status
        # Atualizar status de todos os itens do pedido para o novo status geral, se aplicável
        # ou tratar status de itens individualmente
        for item in pedido.itens:
            if item.status_item_pedido not in [StatusPedido.ENTREGUE_NA_MESA, StatusPedido.ENTREGUE_CLIENTE_EXTERNO, StatusPedido.CANCELADO]:
                item.status_item_pedido = novo_status
        
        db.add(pedido)
        db.commit()
        db.refresh(pedido)

        # Publicar no Redis
        # redis_msg = {
        #     "pedido_id": str(pedido.id),
        #     "novo_status_geral": novo_status.value,
        #     "id_comanda": str(pedido.id_comanda),
        #     "timestamp": datetime.utcnow().isoformat()
        # }
        # await redis_client.publish_message(channel="pedidos_status_updates", message=json.dumps(redis_msg))
        return pedido

    # Outras funções CRUD (get_multi, delete se necessário) podem ser adicionadas.

crud_item_pedido = CRUDItemPedido()
crud_pedido = CRUDPedido()

