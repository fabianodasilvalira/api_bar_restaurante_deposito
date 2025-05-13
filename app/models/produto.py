# app/db/models/produto.py
from sqlalchemy import Column, String, Boolean, Numeric, Text
from app.db.base_class import Base

class Produto(Base):
    nome = Column(String, nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    categoria = Column(String, nullable=True, index=True)
    disponivel = Column(Boolean, default=True)

