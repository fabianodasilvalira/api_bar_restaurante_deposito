# app/schemas/comanda.py
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime # Adicionado para campos de data

from pydantic import BaseModel

from app.db.models.comanda import StatusComanda # Importar o Enum
from app.schemas.cliente import Cliente # Para exibir dados do cliente associado
from app.schemas.mesa import Mesa # Para exibir dados da mesa associada
# from app.schemas.item_pedido import ItemPedido # Para exibir itens do pedido
# from app.schemas.pagamento import Pagamento # Para exibir pagamentos
# from app.schemas.fiado import Fiado # Para exibir fiados

class ComandaBase(BaseModel):
    id_mesa: uuid.UUID
    id_cliente_associado: Optional[uuid.UUID] = None
    status_comanda: Optional[StatusComanda] = StatusComanda.ABERTA
    observacoes: Optional[str] = None

class ComandaCreate(ComandaBase):
    pass # id_mesa é obrigatório

class ComandaUpdate(BaseModel):
    status_comanda: Optional[StatusComanda] = None
    id_cliente_associado: Optional[uuid.UUID] = None
    observacoes: Optional[str] = None
    # valor_total_calculado, valor_pago, valor_fiado são atualizados por outras lógicas (pedidos, pagamentos)

class ComandaInDBBase(ComandaBase):
    id: uuid.UUID
    valor_total_calculado: Decimal
    valor_pago: Decimal
    valor_fiado: Decimal
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class Comanda(ComandaInDBBase):
    mesa: Optional[Mesa] = None # Detalhes da mesa
    cliente: Optional[Cliente] = None # Detalhes do cliente
    # itens_pedido: List[ItemPedido] = []
    # pagamentos: List[Pagamento] = []
    # fiados_registrados: List[Fiado] = []
    pass

# Schema para visualização pública da comanda (via QR Code)
class ComandaDigital(BaseModel):
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

