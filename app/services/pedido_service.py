from asyncio.log import logger
from datetime import datetime, timezone
import uuid
import json
from typing import Optional, Tuple, List, Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.crud.crud_pedido import CRUDPedido
from app.models import Pedido, ItemPedido, Comanda, Produto, Usuario, Mesa
from app.schemas import (
    PedidoCreateSchemas,
    PedidoUpdateSchemas,
    ItemPedidoCreate,
    ItemPedidoUpdate,
    PedidoStatusUpdate
)
from app.crud.base import CRUDBase
from app.services.redis_service import RedisService


class PedidoService:
    def __init__(self):
        self.crud = CRUDPedido()
        self.redis = RedisService()

    async def criar_pedido(
            self,
            db: Session,
            pedido_in: PedidoCreateSchemas,
            current_user: Usuario
    ) -> Tuple[Optional[Pedido], Optional[str]]:
        """
        Cria um novo pedido e seus itens associados
        """
        try:
            # Verifica se a comanda existe e está ativa
            comanda = db.query(Comanda).filter(
                Comanda.id == pedido_in.id_comanda,
                Comanda.status_pagamento.notin_(["Totalmente Pago", "Fiado Fechado"])
            ).first()

            if not comanda:
                return None, "Comanda não encontrada ou já fechada"

            # Cria o pedido principal
            db_pedido = Pedido(
                id_comanda=pedido_in.id_comanda,
                tipo=pedido_in.tipo,
                status="Em preparo",
                observacoes=pedido_in.observacoes,
                id_usuario_solicitante=current_user.id
            )
            db.add(db_pedido)
            db.flush()  # Para obter o ID do pedido

            # Processa os itens do pedido
            total_pedido = 0.0
            itens_validos = []

            for item in pedido_in.itens:
                produto = db.query(Produto).filter(
                    Produto.id == item.id_produto,
                    Produto.disponivel == True
                ).first()

                if not produto:
                    db.rollback()
                    return None, f"Produto {item.id_produto} não encontrado ou indisponível"

                subtotal = produto.preco_unitario * item.quantidade
                db_item = ItemPedido(
                    id_pedido=db_pedido.id,
                    id_produto=item.id_produto,
                    quantidade=item.quantidade,
                    preco_unitario_momento=produto.preco_unitario,
                    subtotal=subtotal,
                    observacoes_item=item.observacoes_item
                )
                itens_validos.append(db_item)
                total_pedido += subtotal

            db.add_all(itens_validos)

            # Atualiza o valor total da comanda
            comanda.valor_total = (comanda.valor_total or 0.0) + total_pedido
            comanda.data_atualizacao = func.now()

            db.commit()
            db.refresh(db_pedido)

            # Notificação via Redis
            await self._notificar_mudanca_pedido(db_pedido, "pedido_criado")

            logger.info(f"Pedido {db_pedido.id} criado com sucesso por {current_user.email}")
            return db_pedido, "Pedido criado com sucesso"

        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar pedido: {str(e)}")
            return None, f"Erro ao criar pedido: {str(e)}"

    async def atualizar_status_pedido(
            self,
            db: Session,
            pedido_id: uuid.UUID,
            status_update: PedidoStatusUpdate,
            current_user: Usuario
    ) -> Tuple[Optional[Pedido], Optional[str]]:
        """
        Atualiza o status de um pedido com validações de transição
        """
        try:
            db_pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
            if not db_pedido:
                return None, "Pedido não encontrado"

            # Valida transições de status
            erro = self._validar_transicao_status(db_pedido.status, status_update.status)
            if erro:
                return None, erro

            # Atualiza o status
            db_pedido.status = status_update.status
            db_pedido.data_ultima_atualizacao_status = func.now()
            db.commit()
            db.refresh(db_pedido)

            # Notificação via Redis
            await self._notificar_mudanca_pedido(db_pedido, "status_atualizado")

            logger.info(
                f"Status do pedido {db_pedido.id} atualizado para {status_update.status} "
                f"por {current_user.email}"
            )
            return db_pedido, f"Status atualizado para {status_update.status}"

        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar status do pedido: {str(e)}")
            return None, f"Erro ao atualizar status: {str(e)}"

    async def adicionar_item_pedido(
            self,
            db: Session,
            pedido_id: uuid.UUID,
            item_in: ItemPedidoCreate,
            current_user: Usuario
    ) -> Tuple[Optional[ItemPedido], Optional[str]]:
        """
        Adiciona um novo item a um pedido existente
        """
        try:
            pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
            if not pedido:
                return None, "Pedido não encontrado"

            if pedido.status in ["Cancelado", "Entregue"]:
                return None, "Não é possível adicionar itens a pedidos cancelados ou entregues"

            produto = db.query(Produto).filter(
                Produto.id == item_in.id_produto,
                Produto.disponivel == True
            ).first()

            if not produto:
                return None, "Produto não encontrado ou indisponível"

            subtotal = produto.preco_unitario * item_in.quantidade
            db_item = ItemPedido(
                id_pedido=pedido_id,
                id_produto=item_in.id_produto,
                quantidade=item_in.quantidade,
                preco_unitario_momento=produto.preco_unitario,
                subtotal=subtotal,
                observacoes_item=item_in.observacoes_item
            )

            db.add(db_item)

            # Atualiza o valor total da comanda
            if pedido.comanda:
                pedido.comanda.valor_total = (pedido.comanda.valor_total or 0.0) + subtotal
                pedido.comanda.data_atualizacao = func.now()

            db.commit()
            db.refresh(db_item)

            # Notificação via Redis
            await self._notificar_mudanca_pedido(pedido, "item_adicionado")

            logger.info(f"Item {db_item.id} adicionado ao pedido {pedido_id} por {current_user.email}")
            return db_item, "Item adicionado com sucesso"

        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao adicionar item ao pedido: {str(e)}")
            return None, f"Erro ao adicionar item: {str(e)}"

    async def _notificar_mudanca_pedido(self, pedido: Pedido, action: str):
        """Envia notificação sobre mudanças no pedido via Redis"""
        message = {
            "pedido_id": str(pedido.id),
            "comanda_id": str(pedido.id_comanda),
            "mesa_id": str(pedido.comanda.id_mesa) if pedido.comanda else None,
            "status": pedido.status,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.redis.publish_message(
            channel="pedidos_updates",
            message=json.dumps(message)
        )

    def _validar_transicao_status(self, status_atual: str, status_novo: str) -> Optional[str]:
        """Valida se a transição de status é permitida"""
        transicoes_permitidas = {
            "Em preparo": ["Saiu para entrega", "Entregue", "Cancelado"],
            "Saiu para entrega": ["Entregue", "Cancelado"],
        }

        if status_atual in ["Entregue", "Cancelado"]:
            return f"Pedido já está {status_atual} e não pode ser alterado"

        if status_novo not in transicoes_permitidas.get(status_atual, []):
            return f"Transição de {status_atual} para {status_novo} não permitida"

        return None


class CRUDPedidoService(CRUDBase[Pedido, PedidoCreateSchemas, PedidoUpdateSchemas]):
    """CRUD específico para Pedidos com operações adicionais"""

    def get_by_comanda(self, db: Session, comanda_id: uuid.UUID) -> List[Pedido]:
        return db.query(self.model).filter(
            self.model.id_comanda == comanda_id
        ).order_by(self.model.data_pedido).all()

    def get_ativos_by_mesa(self, db: Session, mesa_id: uuid.UUID) -> List[Pedido]:
        return db.query(self.model).join(Comanda).filter(
            Comanda.id_mesa == mesa_id,
            self.model.status.notin_(["Entregue", "Cancelado"])
        ).order_by(self.model.data_pedido).all()