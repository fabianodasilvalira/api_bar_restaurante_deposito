# app/db/models/mesa.py
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from app.db.base_class import Base
from app.db.models.cliente import Cliente # Para o relacionamento

class StatusMesa(str, enum.Enum):
    DISPONIVEL = "Disponível"
    OCUPADA = "Ocupada"
    RESERVADA = "Reservada"
    FECHADA = "Fechada" # Quando a conta foi paga, mas pode ser reaberta

class Mesa(Base):
    numero_identificador = Column(String, nullable=False, unique=True, index=True) # Ex: "Mesa 01", "Balcão 03"
    capacidade = Column(Integer, nullable=True)
    status = Column(SAEnum(StatusMesa), default=StatusMesa.DISPONIVEL, nullable=False)
    qr_code_hash = Column(String, nullable=True, unique=True, index=True) # Hash para identificar a comanda via QR Code

    # Relacionamento com Cliente (opcional, uma mesa pode ou não estar associada a um cliente específico no momento)
    id_cliente_associado = Column(ForeignKey("clientes.id"), nullable=True)
    cliente_associado = relationship("Cliente", back_populates="mesas_associadas")

    # Relacionamento com Comanda (uma mesa pode ter várias comandas ao longo do tempo, mas geralmente uma ativa)
    comandas = relationship("Comanda", back_populates="mesa", order_by="desc(Comanda.data_criacao)")

    # Poderia ter um relacionamento com o usuário (garçom) responsável pela mesa atualmente
    # id_usuario_responsavel = Column(ForeignKey("usuarios.id"), nullable=True)
    # usuario_responsavel = relationship("Usuario", back_populates="mesas_abertas")

