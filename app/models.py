# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from .database import Base # Assuming database.py defines Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    cargo = Column(String) # e.g., 'garcom', 'caixa', 'gerente'
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, index=True)
    telefone = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    observacoes = Column(Text, nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    comandas_fiado = relationship("Fiado", back_populates="cliente")

class Produto(Base):
    __tablename__ = "produtos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, index=True, nullable=False)
    descricao = Column(Text, nullable=True)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    categoria = Column(String, index=True)
    disponivel = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

class Mesa(Base):
    __tablename__ = "mesas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_identificador = Column(String, unique=True, nullable=False)
    capacidade = Column(Integer, nullable=False)
    status = Column(String, default="Livre")  # Livre, Ocupada, Reservada, Interditada
    localizacao = Column(String, nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    comandas = relationship("Comanda", back_populates="mesa")

class Comanda(Base):
    __tablename__ = "comandas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mesa_id = Column(UUID(as_uuid=True), ForeignKey("mesas.id"))
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios_internos.id"), nullable=True) # Garçom ou responsável
    status = Column(String, default="Aberta")  # Aberta, Fechada, Paga, Cancelada
    valor_total = Column(Numeric(10, 2), default=0.00)
    valor_pago = Column(Numeric(10, 2), default=0.00)
    data_abertura = Column(DateTime(timezone=True), server_default=func.now())
    data_fechamento = Column(DateTime(timezone=True), nullable=True)

    mesa = relationship("Mesa", back_populates="comandas")
    cliente = relationship("Cliente")
    usuario = relationship("Usuario")
    pedidos = relationship("Pedido", back_populates="comanda")
    pagamentos = relationship("Pagamento", back_populates="comanda")
    fiados = relationship("Fiado", back_populates="comanda_origem")

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comanda_id = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    data_pedido = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="Recebido") # Recebido, Em Preparo, Entregue, Cancelado

    comanda = relationship("Comanda", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario_momento = Column(Numeric(10, 2), nullable=False) # Preço no momento do pedido
    observacoes = Column(Text, nullable=True)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")

class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comanda_id = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    metodo_pagamento = Column(String, nullable=False) # Dinheiro, Cartão Crédito, Cartão Débito, Pix
    data_pagamento = Column(DateTime(timezone=True), server_default=func.now())
    id_usuario_responsavel = Column(UUID(as_uuid=True), ForeignKey("usuarios_internos.id"), nullable=True) # Caixa ou Garçom

    comanda = relationship("Comanda", back_populates="pagamentos")
    usuario_responsavel = relationship("Usuario")

class Fiado(Base):
    __tablename__ = "fiados"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comanda_id = Column(UUID(as_uuid=True), ForeignKey("comandas.id"), nullable=False)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    valor_devido = Column(Numeric(10, 2), nullable=False)
    data_vencimento = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="Pendente") # Pendente, Pago Parcialmente, Pago Totalmente, Atrasado
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_ultima_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

    comanda_origem = relationship("Comanda", back_populates="fiados")
    cliente = relationship("Cliente", back_populates="comandas_fiado")

