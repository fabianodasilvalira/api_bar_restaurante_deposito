from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import uuid
from datetime import datetime
from decimal import Decimal

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Usuario Schemas ---
class UsuarioInternoBase(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = None
    cargo: Optional[str] = None
    ativo: Optional[bool] = True

class UsuarioInternoCreate(UsuarioInternoBase):
    password: str

class Usuario(UsuarioInternoBase):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Cliente Schemas ---
class ClienteBase(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Produto Schemas ---
class ProdutoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco_unitario: Decimal
    categoria: Optional[str] = None
    disponivel: Optional[bool] = True

class ProdutoCreate(ProdutoBase):
    pass

class Produto(ProdutoBase):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- ItemPedido Schemas ---
class ItemPedidoBase(BaseModel):
    id_produto: uuid.UUID
    quantidade: int
    observacoes_item: Optional[str] = None

class ItemPedidoCreate(ItemPedidoBase):
    pass # preco_unitario_momento and subtotal will be set in CRUD

class ItemPedido(ItemPedidoBase):
    id: uuid.UUID
    preco_unitario_momento: Decimal
    subtotal: Decimal
    produto: Produto # To show product details

    class Config:
        from_attributes = True

# --- Pedido Schemas ---
class PedidoBase(BaseModel):
    tipo: Optional[str] = "Interno"
    observacoes: Optional[str] = None

class PedidoCreate(PedidoBase):
    itens: List[ItemPedidoCreate]

class Pedido(PedidoBase):
    id: uuid.UUID
    id_comanda: uuid.UUID
    status: str
    data_pedido: datetime
    data_ultima_atualizacao_status: datetime
    id_usuario_solicitante: Optional[uuid.UUID] = None
    itens_pedido: List[ItemPedido] = []
    usuario_solicitante: Optional[Usuario] = None # To show who made the order

    class Config:
        from_attributes = True

# --- Pagamento Schemas ---
class PagamentoBase(BaseModel):
    valor: Decimal
    metodo_pagamento: str # Dinheiro, Cartão Crédito, Cartão Débito, Pix
    observacoes: Optional[str] = None

class PagamentoCreate(PagamentoBase):
    pass

class Pagamento(PagamentoBase):
    id: uuid.UUID
    id_comanda: uuid.UUID
    data_pagamento: datetime
    id_usuario_registrou: Optional[uuid.UUID] = None
    usuario_registrou: Optional[Usuario] = None

    class Config:
        from_attributes = True

# --- Comanda Schemas ---
class ComandaBase(BaseModel):
    pass # Most fields are derived or set internally

class ComandaCreate(ComandaBase):
    # id_mesa is passed via URL or context
    id_cliente_associado: Optional[uuid.UUID] = None

class Comanda(ComandaBase):
    id: uuid.UUID
    id_mesa: uuid.UUID
    valor_total: Decimal
    valor_pago: Decimal
    valor_fiado: Decimal
    status_pagamento: str
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None
    pedidos: List[Pedido] = []
    pagamentos: List[Pagamento] = []
    # cliente_associado: Optional[Cliente] = None # If needed

    class Config:
        from_attributes = True

# --- Mesa Schemas ---
class MesaBase(BaseModel):
    numero_identificador: str
    id_cliente_associado: Optional[uuid.UUID] = None

class MesaCreate(MesaBase):
    pass

class Mesa(MesaBase):
    id: uuid.UUID
    qr_code_hash: Optional[str] = None
    status: str
    data_abertura: Optional[datetime] = None
    data_fechamento: Optional[datetime] = None
    id_usuario_responsavel: Optional[uuid.UUID] = None
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None
    usuario_responsavel: Optional[Usuario] = None
    cliente_associado: Optional[Cliente] = None
    comanda_ativa: Optional[Comanda] = None

    class Config:
        from_attributes = True

# --- Fiado Schemas ---
class FiadoBase(BaseModel):
    id_cliente: uuid.UUID
    valor_devido: Decimal
    data_vencimento: Optional[datetime] = None
    status: Optional[str] = "Pendente"

class FiadoCreate(FiadoBase):
    id_comanda_origem: uuid.UUID

class Fiado(FiadoBase):
    id: uuid.UUID
    id_comanda_origem: uuid.UUID
    data_criacao: datetime
    data_ultima_atualizacao: Optional[datetime] = None
    cliente: Cliente
    comanda_origem: Comanda # To show details of the original comanda

    class Config:
        from_attributes = True

# Schema for QR Code access (public)
class ComandaPublic(BaseModel):
    id: uuid.UUID
    numero_mesa: str
    valor_total: Decimal
    status_pagamento: str
    pedidos: List[Pedido] = [] # Simplified pedido view if needed

    class Config:
        from_attributes = True


# --- Relatório Fiado Schemas ---
class RelatorioFiadoItem(BaseModel):
    id_cliente: uuid.UUID
    nome_cliente: Optional[str] = "Cliente não informado"
    valor_total_devido: Decimal
    quantidade_fiados_pendentes: int
    # data_ultimo_fiado: Optional[datetime] = None # Could be useful

    class Config:
        from_attributes = True

class RelatorioFiado(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_geral_devido: Decimal
    total_fiados_registrados_periodo: int
    detalhes_por_cliente: List[RelatorioFiadoItem]

    class Config:
        from_attributes = True

