# app/schemas/comanda.py
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime # Adicionado para campos de data

from pydantic import BaseModel

from app.db.models.comanda import StatusComanda # Importar o Enum
from app.schemas.cliente import ClienteSchemas # Para exibir dados do cliente associado
from app.schemas.mesa import MesaSchemas # Para exibir dados da mesa associada
# from app.schemas.item_pedido import ItemPedido # Para exibir itens do pedido
# from app.schemas.pagamento import Pagamento # Para exibir pagamentos
# from app.schemas.fiado import Fiado # Para exibir fiados

class ComandaBaseSchemas(BaseModel):
    id_mesa: uuid.UUID
    id_cliente_associado: Optional[uuid.UUID] = None
    status_comanda: Optional[StatusComanda] = StatusComanda.ABERTA
    observacoes: Optional[str] = None

class ComandaCreateSchemas(ComandaBaseSchemas):
    pass # id_mesa é obrigatório

class ComandaUpdateSchemas(BaseModel):
    status_comanda: Optional[StatusComanda] = None
    id_cliente_associado: Optional[uuid.UUID] = None
    observacoes: Optional[str] = None
    # valor_total_calculado, valor_pago, valor_fiado são atualizados por outras lógicas (pedidos, pagamentos)

class ComandaInDBBaseSchemas(ComandaBaseSchemas):
    id: uuid.UUID
    valor_total_calculado: Decimal
    valor_pago: Decimal
    valor_fiado: Decimal
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class ComandaSchemas(ComandaInDBBaseSchemas):
    mesa: Optional[MesaSchemas] = None # Detalhes da mesa
    cliente: Optional[ClienteSchemas] = None # Detalhes do cliente
    # itens_pedido: List[ItemPedido] = []
    # pagamentos: List[Pagamento] = []
    # fiados_registrados: List[Fiado] = []
    pass

# Schema para visualização pública da comanda (via QR Code)
class ComandaDigitalSchemas(BaseModel):
    id: uuid.UUID
    numero_mesa: str
    status_comanda: StatusComanda
    valor_total_calculado: Decimal
    valor_pago: Decimal
    valor_restante: Decimal # Calculado (total - pago)
    # itens: List[ItemPedidoComandaDigital] # Schema simplificado para itens
    data_abertura: datetime
    # observacoes_cliente: Optional[str] = None # Se houver campo específico para cliente

    class Config:
        from_attributes = True




# Schema para itens da comanda digital (visualização do cliente)
class ItemPedidoComandaDigitalSchemas(BaseModel):
    nome_produto: str
    quantidade: int
    preco_total_item: Decimal
    status_item_pedido: Optional[str] = None # Ex: "Preparando", "Pronto", "Entregue"
    observacoes: Optional[str] = None

    class Config:
        from_attributes = True

