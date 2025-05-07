# app/schemas/pedido.py
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, validator

from app.db.models.pedido import StatusPedido, TipoPedido # Importar Enums
from app.schemas.produto import Produto # Para exibir dados do produto no item
# from app.schemas.usuario import Usuario # Para exibir dados do usuário que registrou

# --- ItemPedido Schemas ---
class ItemPedidoBase(BaseModel):
    id_produto: uuid.UUID
    quantidade: int
    observacoes_item: Optional[str] = None

    @validator("quantidade")
    def quantidade_deve_ser_positiva(cls, v):
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v

class ItemPedidoCreate(ItemPedidoBase):
    # preco_unitario_no_momento e preco_total_item serão definidos no backend
    pass

class ItemPedidoUpdate(BaseModel):
    quantidade: Optional[int] = None
    observacoes_item: Optional[str] = None
    status_item_pedido: Optional[StatusPedido] = None

    @validator("quantidade", pre=True, always=True)
    def quantidade_opcional_deve_ser_positiva(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v

class ItemPedidoInDBBase(ItemPedidoBase):
    id: uuid.UUID
    id_pedido: uuid.UUID
    id_comanda: uuid.UUID # Denormalizado
    preco_unitario_no_momento: Decimal
    preco_total_item: Decimal
    status_item_pedido: StatusPedido
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class ItemPedido(ItemPedidoInDBBase):
    produto: Optional[Produto] = None # Detalhes do produto
    pass

# --- Pedido Schemas ---
class PedidoBase(BaseModel):
    id_comanda: uuid.UUID
    # id_cliente_solicitante: Optional[uuid.UUID] = None
    tipo_pedido: Optional[TipoPedido] = TipoPedido.INTERNO_MESA
    observacoes_pedido: Optional[str] = None

class PedidoCreate(PedidoBase):
    itens: List[ItemPedidoCreate]

class PedidoUpdate(BaseModel):
    status_geral_pedido: Optional[StatusPedido] = None
    observacoes_pedido: Optional[str] = None
    # Itens de um pedido geralmente não são atualizados diretamente no pedido; 
    # ou se cancela o item, ou se adiciona um novo pedido/item.
    # Se for necessário atualizar itens, um endpoint específico para itens de pedido seria melhor.

class PedidoInDBBase(PedidoBase):
    id: uuid.UUID
    id_usuario_registrou: Optional[uuid.UUID] = None
    status_geral_pedido: StatusPedido
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class Pedido(PedidoInDBBase):
    # usuario_registrou: Optional[Usuario] = None
    itens: List[ItemPedido] = []
    pass

# Schema para notificação de atualização de status de pedido via Redis
class PedidoStatusUpdateNotification(BaseModel):
    pedido_id: uuid.UUID
    item_pedido_id: Optional[uuid.UUID] = None # Se a atualização for de um item específico
    novo_status: StatusPedido
    id_comanda: uuid.UUID
    id_mesa: Optional[uuid.UUID] = None # Para facilitar o direcionamento no frontend da mesa
    timestamp: datetime

