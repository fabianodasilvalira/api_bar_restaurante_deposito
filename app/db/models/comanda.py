# app/db/models/comanda.py
import enum
import uuid
from sqlalchemy import Column, ForeignKey, Enum as SAEnum, Numeric, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base
# from app.db.models.mesa import Mesa # Para relacionamento, já importado em Mesa
# from app.db.models.cliente import Cliente # Para relacionamento

class StatusComanda(str, enum.Enum):
    ABERTA = "Aberta"
    FECHADA = "Fechada" # Cliente solicitou fechamento, aguardando pagamento
    PAGA_PARCIALMENTE = "Paga Parcialmente"
    PAGA_TOTALMENTE = "Paga Totalmente"
    CANCELADA = "Cancelada"
    EM_FIADO = "Em Fiado"

class Comanda(Base):
    # id, data_criacao, data_atualizacao são herdados da Base

    id_mesa = Column(ForeignKey("mesas.id"), nullable=False)
    id_cliente_associado = Column(ForeignKey("clientes.id"), nullable=True) # Cliente que abriu/está na comanda
    # id_usuario_responsavel = Column(ForeignKey("usuarios.id"), nullable=True) # Garçom que abriu/gerencia

    status_comanda = Column(SAEnum(StatusComanda), default=StatusComanda.ABERTA, nullable=False)
    valor_total_calculado = Column(Numeric(10, 2), default=0.00, nullable=False)
    valor_pago = Column(Numeric(10, 2), default=0.00, nullable=False)
    valor_fiado = Column(Numeric(10, 2), default=0.00, nullable=False)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    mesa = relationship("Mesa", back_populates="comandas")
    cliente = relationship("Cliente") # Se precisar de back_populates, adicionar em Cliente
    # usuario_responsavel = relationship("Usuario")

    itens_pedido = relationship("ItemPedido", back_populates="comanda", cascade="all, delete-orphan")
    pagamentos = relationship("Pagamento", back_populates="comanda", cascade="all, delete-orphan")
    fiados_registrados = relationship("Fiado", back_populates="comanda", cascade="all, delete-orphan")

    # Propriedade para fácil acesso à comanda ativa de uma mesa (pode ser uma lógica no CRUD)
    # @property
    # def is_ativa(self) -> bool:
    #     return self.status_comanda in [StatusComanda.ABERTA, StatusComanda.PAGA_PARCIALMENTE]

