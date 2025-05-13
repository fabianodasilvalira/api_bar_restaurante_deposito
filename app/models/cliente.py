# app/db/models/cliente.py
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Cliente(Base):
    nome = Column(String, nullable=True, index=True)
    telefone = Column(String, nullable=True, index=True, unique=True) # Telefone pode ser um bom identificador único
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    mesas_associadas = relationship("Mesa", back_populates="cliente_associado")
    comandas_fiado = relationship("Fiado", back_populates="cliente")

