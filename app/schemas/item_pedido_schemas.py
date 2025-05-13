# app/schemas/item_pedido_schemas.py
from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field

class ItemPedidoBase(BaseModel):
    produto_id: UUID
    quantidade: int = Field(..., gt=0)
    preco_unitario_momento: Decimal = Field(..., gt=0)
    observacoes: Optional[str] = None

class ItemPedidoCreate(ItemPedidoBase):
    pass

class ItemPedidoUpdate(BaseModel):
    quantidade: Optional[int] = Field(None, gt=0)
    observacoes: Optional[str] = None

class ItemPedido(ItemPedidoBase):
    id: UUID
    pedido_id: UUID

    class Config:
        from_attributes = True

