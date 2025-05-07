# app/db/models/pagamento.py
import enum
import uuid
from sqlalchemy import Column, ForeignKey, Enum as SAEnum, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class MetodoPagamento(str, enum.Enum):
    DINHEIRO = "Dinheiro"
    CARTAO_CREDITO = "Cartão de Crédito"
    CARTAO_DEBITO = "Cartão de Débito"
    PIX = "Pix"
    FIADO = "Fiado" # Usado para registrar a parte que vai para o fiado
    OUTRO = "Outro"

class StatusPagamento(str, enum.Enum):
    PENDENTE = "Pendente"
    APROVADO = "Aprovado"
    REJEITADO = "Rejeitado"
    CANCELADO = "Cancelado"

class Pagamento(Base):
    id_comanda = Column(ForeignKey("comandas.id"), nullable=False)
    id_cliente = Column(ForeignKey("clientes.id"), nullable=True) # Cliente que efetuou o pagamento
    id_usuario_registrou = Column(ForeignKey("usuarios.id"), nullable=True) # Funcionário que registrou

    valor_pago = Column(Numeric(10, 2), nullable=False)
    metodo_pagamento = Column(SAEnum(MetodoPagamento), nullable=False)
    status_pagamento = Column(SAEnum(StatusPagamento), default=StatusPagamento.APROVADO, nullable=False)
    detalhes_transacao = Column(String, nullable=True) # Ex: ID da transação do gateway
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    comanda = relationship("Comanda", back_populates="pagamentos")
    cliente = relationship("Cliente")
    usuario_registrou = relationship("Usuario")

