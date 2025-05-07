# app/schemas/produto.py
from typing import Optional
import uuid
from decimal import Decimal
from pydantic import BaseModel

class ProdutoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco_unitario: Decimal
    categoria: Optional[str] = None
    disponivel: Optional[bool] = True

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoUpdate(ProdutoBase):
    nome: Optional[str] = None # All fields optional for update
    preco_unitario: Optional[Decimal] = None
    disponivel: Optional[bool] = None

class ProdutoInDBBase(ProdutoBase):
    id: uuid.UUID
    # data_criacao: datetime # from Base model
    # data_atualizacao: Optional[datetime] = None # from Base model

    class Config:
        from_attributes = True

class Produto(ProdutoInDBBase):
    pass

