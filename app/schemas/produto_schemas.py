# app/schemas/produto_schemas.py
from typing import Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field

class ProdutoBase(BaseModel):
    nome: str = Field(..., example="Pizza Margherita")
    descricao: Optional[str] = Field(None, example="Molho de tomate, mozzarella e manjericão fresco")
    preco_unitario: Decimal = Field(..., gt=0, example=35.50)
    categoria: Optional[str] = Field(None, example="Pizzas")
    disponivel: bool = True

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco_unitario: Optional[Decimal] = Field(None, gt=0)
    categoria: Optional[str] = None
    disponivel: Optional[bool] = None

class Produto(ProdutoBase):
    id: UUID

    class Config:
        from_attributes = True

