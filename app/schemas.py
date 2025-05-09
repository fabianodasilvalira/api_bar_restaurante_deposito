from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

# --- Token Schemas ---
class TokenSchemas(BaseModel):
    access_token: str
    token_type: str

class TokenDataSchemas(BaseModel):
    email: Optional[str] = None

# --- Usuario Schemas ---
class UsuarioInternoBaseSchemas(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = None
    cargo: Optional[str] = None
    ativo: Optional[bool] = True

class UsuarioInternoCreateSchemas(UsuarioInternoBaseSchemas):
    password: str

class UsuarioSchemas(UsuarioInternoBaseSchemas):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Cliente Schemas ---
class ClienteBaseSchemas(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None

class ClienteCreateSchemas(ClienteBaseSchemas):
    pass

class ClienteSchemas(ClienteBaseSchemas):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Produto Schemas ---
class ProdutoBaseSchemas(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco_unitario: Decimal
    categoria: Optional[str] = None
    disponivel: Optional[bool] = True

class ProdutoCreateSchemas(ProdutoBaseSchemas):
    pass

class ProdutoSchemas(ProdutoBaseSchemas):
    id: uuid.UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- ItemPedido Schemas ---
class ItemPedidoBaseSchemas(BaseModel):
    id_produto: uuid.UUID
    quantidade: int
    observacoes_item: Optional[str] = None

class ItemPedidoCreateSchemas(ItemPedidoBaseSchemas):
    pass  # preco_unitario_momento e subtotal serão definidos no backend

class ItemPedidoSchemas(ItemPedidoBaseSchemas):
    id: uuid.UUID
    preco_unitario_momento: Decimal
    subtotal: Decimal
    produto: Produto

    class Config:
        from_attributes = True

# --- Pedido Schemas ---
class PedidoBaseSchemas(BaseModel):
    tipo: Optional[str] = "Interno"
    observacoes: Optional[str] = None

class PedidoCreateSchemas(PedidoBaseSchemas):
    itens: List[ItemPedidoCreate]

class PedidoSchemas(PedidoBaseSchemas):
    id: uuid.UUID
    id_comanda: uuid.UUID
    status: str
    data_pedido: datetime
    data_ultima_atualizacao_status: datetime
    id_usuario_solicitante: Optional[uuid.UUID] = None
    itens_pedido: List[ItemPedido] = []
    usuario_solicitante: Optional[Usuario] = None

    class Config:
        from_attributes = True

# --- Pagamento Schemas ---
class PagamentoBaseSchemas(BaseModel):
    valor: Decimal
    metodo_pagamento: str  # Dinheiro, Cartão Crédito, Cartão Débito, Pix
    observacoes: Optional[str] = None

class PagamentoCreateSchemas(PagamentoBaseSchemas):
    pass

class PagamentoSchemas(PagamentoBaseSchemas):
    id: uuid.UUID
    id_comanda: uuid.UUID
    data_pagamento: datetime
    id_usuario_registrou: Optional[uuid.UUID] = None
    usuario_registrou: Optional[Usuario] = None

    class Config:
        from_attributes = True

# --- Comanda Schemas ---
class ComandaBaseSchemas(BaseModel):
    pass  # Campos preenchidos internamente

class ComandaCreateSchemas(ComandaBaseSchemas):
    id_cliente_associado: Optional[uuid.UUID] = None

class ComandaSchemas(ComandaBaseSchemas):
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

    class Config:
        from_attributes = True

# --- Mesa Schemas ---
class MesaBaseSchemas(BaseModel):
    numero_identificador: str
    id_cliente_associado: Optional[uuid.UUID] = None

class MesaCreateSchemas(MesaBaseSchemas):
    pass

class MesaSchemas(MesaBaseSchemas):
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
class FiadoBaseSchemas(BaseModel):
    id_cliente: uuid.UUID
    valor_devido: Decimal
    data_vencimento: Optional[datetime] = None
    status: Optional[str] = "Pendente"

class FiadoCreateSchemas(FiadoBaseSchemas):
    id_comanda_origem: uuid.UUID

class FiadoSchemas(FiadoBaseSchemas):
    id: uuid.UUID
    id_comanda_origem: uuid.UUID
    data_criacao: datetime
    data_ultima_atualizacao: Optional[datetime] = None
    cliente: Cliente
    comanda_origem: Comanda

    class Config:
        from_attributes = True

# --- Comanda Pública (via QR Code) ---
class ComandaPublicSchemas(BaseModel):
    id: uuid.UUID
    numero_mesa: str
    valor_total: Decimal
    status_pagamento: str
    pedidos: List[Pedido] = []

    class Config:
        from_attributes = True

# --- Relatório Fiado Schemas ---
class RelatorioFiadoItemSchemas(BaseModel):
    id_cliente: uuid.UUID
    nome_cliente: Optional[str] = "Cliente não informado"
    valor_total_devido: Decimal
    quantidade_fiados_pendentes: int

    class Config:
        from_attributes = True

class RelatorioFiadoSchemas(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_geral_devido: Decimal
    total_fiados_registrados_periodo: int
    detalhes_por_cliente: List[RelatorioFiadoItem]

    class Config:
        from_attributes = True
