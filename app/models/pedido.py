# app/db/models/pedido.py
import enum
import uuid
from sqlalchemy import Column, ForeignKey, Enum as SAEnum, Integer, Numeric, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # Para func.now()

from app.db.base_class import Base
# from app.db.models.comanda import Comanda # Para relacionamento
# from app.db.models.produto import Produto # Para relacionamento
# from app.db.models.usuario import Usuario # Para relacionamento (quem registrou o pedido)

class StatusPedido(str, enum.Enum):
    RECEBIDO = "Recebido" # Pedido feito pelo cliente/garçom, aguardando preparo
    EM_PREPARO = "Em Preparo"
    PRONTO_PARA_ENTREGA = "Pronto para Entrega" # Para cozinha/bar avisar que está pronto
    ENTREGUE_NA_MESA = "Entregue na Mesa" # Para pedidos internos
    SAIU_PARA_ENTREGA_EXTERNA = "Saiu para Entrega (Externa)"
    ENTREGUE_CLIENTE_EXTERNO = "Entregue (Cliente Externo)"
    CANCELADO = "Cancelado"

class TipoPedido(str, enum.Enum):
    INTERNO_MESA = "Interno (Mesa)"
    EXTERNO_DELIVERY = "Externo (Delivery)"
    EXTERNO_RETIRADA = "Externo (Retirada)"

class Pedido(Base):
    """Representa um pedido geral, que pode conter vários itens."""
    # id, data_criacao, data_atualizacao são herdados da Base

    id_comanda = Column(ForeignKey("comandas.id"), nullable=False) # Todo pedido pertence a uma comanda
    # id_cliente_solicitante = Column(ForeignKey("clientes.id"), nullable=True) # Se o cliente fez o pedido diretamente
    id_usuario_registrou = Column(ForeignKey("usuarios.id"), nullable=True) # Garçom/Atendente que registrou

    tipo_pedido = Column(SAEnum(TipoPedido), default=TipoPedido.INTERNO_MESA, nullable=False)
    status_geral_pedido = Column(SAEnum(StatusPedido), default=StatusPedido.RECEBIDO, nullable=False)
    observacoes_pedido = Column(Text, nullable=True)
    # data_hora_entrega_estimada = Column(DateTime(timezone=True), nullable=True)
    # data_hora_entregue = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    comanda = relationship("Comanda") # Um pedido pertence a uma comanda
    # cliente_solicitante = relationship("Cliente")
    usuario_registrou = relationship("Usuario")
    itens = relationship("ItemPedido", back_populates="pedido_pai", cascade="all, delete-orphan")

class ItemPedido(Base):
    """Representa um item específico dentro de um Pedido."""
    # id, data_criacao, data_atualizacao são herdados da Base

    id_pedido = Column(ForeignKey("pedidos.id"), nullable=False)
    id_comanda = Column(ForeignKey("comandas.id"), nullable=False) # Denormalizado para facilitar consulta na comanda
    id_produto = Column(ForeignKey("produtos.id"), nullable=False)

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario_no_momento = Column(Numeric(10, 2), nullable=False) # Preço do produto no momento do pedido
    preco_total_item = Column(Numeric(10, 2), nullable=False) # quantidade * preco_unitario_no_momento
    observacoes_item = Column(Text, nullable=True)
    status_item_pedido = Column(SAEnum(StatusPedido), default=StatusPedido.RECEBIDO, nullable=False)

    # Relacionamentos
    pedido_pai = relationship("Pedido", back_populates="itens")
    comanda = relationship("Comanda", back_populates="itens_pedido")
    produto = relationship("Produto")

