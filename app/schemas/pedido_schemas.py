# app/schemas/pedido_schemas.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from .item_pedido_schemas import ItemPedido, ItemPedidoCreate # Assuming these are defined elsewhere
from .usuario_schemas import UsuarioSchemas # Assuming UsuarioSchemas is defined
from enum import Enum

class StatusPedido(Enum):
    PENDENTE = "Pendente"
    FINALIZADO = "Finalizado"
    CANCELADO = "Cancelado"

class PedidoBaseSchemas(BaseModel):
    mesa_id: UUID
    cliente_id: Optional[UUID] = None
    observacoes: Optional[str] = None

class PedidoCreateSchemas(PedidoBaseSchemas):
    itens: List[ItemPedidoCreate]

class PedidoUpdateSchemas(BaseModel):
    status: Optional[str] = None
    observacoes: Optional[str] = None
    itens_to_add: Optional[List[ItemPedidoCreate]] = None
    itens_to_remove: Optional[List[UUID]] = None # List of ItemPedido IDs to remove

class PedidoSchemas(PedidoBaseSchemas):
    id: UUID
    status: str
    data_pedido: datetime
    data_ultima_atualizacao: datetime
    valor_total: float
    usuario_id: Optional[UUID] = None

    itens_pedido: List[ItemPedido] = []
    usuario: Optional[UsuarioSchemas] = None

    class Config:
        from_attributes = True

