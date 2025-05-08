from sqlalchemy import (
    Column, String, Boolean, DateTime, func,
    ForeignKey, Integer, Numeric, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, object_session
import uuid
from .database import Base

# =======================
# MODELO: Usuário Interno
# =======================
class Usuario(Base):
    __tablename__ = "usuarios_internos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    cargo = Column(String, nullable=True)  # Ex: "Garçom", "Gerente", "Caixa"
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())


# ==================
# MODELO: Cliente
# ==================
class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=True)
    telefone = Column(String, nullable=True, index=True)
    observacoes = Column(Text, nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamento com registros de fiado
    comandas_fiado = relationship("Fiado", back_populates="cliente")


# ==================
# MODELO: Mesa
# ==================
class Mesa(Base):
    __tablename__ = "mesas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_identificador = Column(String, unique=True, nullable=False, index=True)
    qr_code_hash = Column(String, unique=True, nullable=True, index=True)
    status = Column(String, default="Livre")  # Livre, Ocupada, Reservada
    data_abertura = Column(DateTime(timezone=True), nullable=True)
    data_fechamento = Column(DateTime(timezone=True), nullable=True)

    id_usuario_responsavel = Column(UUID(as_uuid=True), ForeignKey("usuarios_internos.id"), nullable=True)
    id_cliente_associado = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)

    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    usuario_responsavel = relationship("Usuario")
    cliente_associado = relationship("Cliente")
    comandas = relationship("Comanda", back_populates="mesa")

    # Retorna comanda ativa (ainda não paga totalmente)
    def get_comanda_ativa(self):
        session = object_session(self)
        if session is None:
            return None
        return session.query(Comanda).filter(
            Comanda.id_mesa == self.id,
            Comanda.status_pagamento.notin_(["Totalmente Pago", "Fiado Fechado"])
        ).first()


# ====================
# MODELO: Produto
# ====================
class Produto(Base):
    __tablename__ = "produtos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    categoria = Column(String, nullable=True, index=True)
    disponivel = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())


# ====================
# MODELO: Comanda
# ====================
class Comanda(Base):
    __tablename__ = "comandas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_mesa = Column(UUID(as_uuid=True), ForeignKey("mesas.id"), nullable=False)
    valor_total = Column(Numeric(10, 2), default=0.00)
    valor_pago = Column(Numeric(10, 2), default=0.00)
    valor_fiado = Column(Numeric(10, 2), default=0.00)
    status_pagamento = Column(String, default="Pendente")  # Pendente, Parcialmente Pago, Totalmente Pago, Fiado, Fiado Fechado

    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    mesa = relationship("Mesa", back_populates="comandas")
    pedidos = relationship("Pedido", back_populates="comanda")
    pagamentos = relationship("Pagamento", back_populates="comanda")
    registros_fiado = relationship("Fiado", back_populates="comanda_origem")


# ==================
# MODELO: Pedido
# ==================
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_comanda = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    tipo = Column(String, default="Interno")  # Interno, Externo/Delivery
    status = Column(String, default="Em preparo")  # Em preparo, Entregue, Saiu para entrega, Cancelado
    observacoes = Column(Text, nullable=True)
    id_usuario_solicitante = Column(UUID(as_uuid=True), ForeignKey("usuarios_internos.id"), nullable=True)

    data_pedido = Column(DateTime(timezone=True), server_default=func.now())
    data_ultima_atualizacao_status = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    comanda = relationship("Comanda", back_populates="pedidos")
    usuario_solicitante = relationship("Usuario")
    itens_pedido = relationship("ItemPedido", back_populates="pedido")


# ======================
# MODELO: Item do Pedido
# ======================
class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_pedido = Column(UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=False)
    id_produto = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario_momento = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    observacoes_item = Column(Text, nullable=True)

    # Relacionamentos
    pedido = relationship("Pedido", back_populates="itens_pedido")
    produto = relationship("Produto")


# ======================
# MODELO: Pagamento
# ======================
class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_comanda = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    metodo_pagamento = Column(String, nullable=False)  # Dinheiro, Cartão Crédito, Cartão Débito, Pix
    data_pagamento = Column(DateTime(timezone=True), server_default=func.now())
    id_usuario_registrou = Column(UUID(as_uuid=True), ForeignKey("usuarios_internos.id"), nullable=True)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    comanda = relationship("Comanda", back_populates="pagamentos")
    usuario_registrou = relationship("Usuario")


# ===================
# MODELO: Fiado
# ===================
class Fiado(Base):
    __tablename__ = "fiados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_comanda_origem = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    id_cliente = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    valor_devido = Column(Numeric(10, 2), nullable=False)
    data_vencimento = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="Pendente")  # Pendente, Pago Parcialmente, Pago Totalmente, Atrasado

    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_ultima_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    comanda_origem = relationship("Comanda", back_populates="registros_fiado")
    cliente = relationship("Cliente", back_populates="comandas_fiado")
