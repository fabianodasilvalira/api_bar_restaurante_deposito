# app/db/models/fiado.py
import enum
import uuid
from sqlalchemy import Column, ForeignKey, Enum as SAEnum, Numeric, Text, Date
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class StatusFiado(str, enum.Enum):
    PENDENTE = "Pendente"
    PAGO_PARCIALMENTE = "Pago Parcialmente"
    PAGO_TOTALMENTE = "Pago Totalmente"
    CANCELADO = "Cancelado"

class Fiado(Base):
    id_comanda = Column(ForeignKey("comandas.id"), nullable=False)
    id_cliente = Column(ForeignKey("clientes.id"), nullable=False)
    id_usuario_registrou = Column(ForeignKey("usuarios.id"), nullable=True)

    valor_original = Column(Numeric(10, 2), nullable=False)
    valor_devido = Column(Numeric(10, 2), nullable=False) # Valor que ainda falta pagar deste fiado específico
    status_fiado = Column(SAEnum(StatusFiado), default=StatusFiado.PENDENTE, nullable=False)
    data_vencimento = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    comanda = relationship("Comanda", back_populates="fiados_registrados")
    cliente = relationship("Cliente", back_populates="comandas_fiado")
    usuario_registrou = relationship("Usuario")
    # pagamentos_fiado = relationship("PagamentoFiado", back_populates="fiado") # Se houver pagamentos específicos para o fiado

