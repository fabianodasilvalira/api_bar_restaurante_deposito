# app/schemas/comanda_schemas.py
from typing import Optional, List
import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

class StatusComanda(str, Enum):
    ABERTA = "Aberta"
    FECHADA = "Fechada"
    PAGA = "Paga"
    PARCIALMENTE_PAGA = "Parcialmente Paga"
    FIADO = "Fiado"



class Pedido(BaseModel):
    id: uuid.UUID
    status: str
    valor_total_pedido: Optional[Decimal] = None
    # Add other relevant fields from PedidoSchemas as needed for display in Comanda
    class Config:
        from_attributes = True

# Placeholder for PagamentoSchemas - replace with actual import or definition
class Pagamento(BaseModel):
    id: uuid.UUID
    valor: Decimal
    metodo_pagamento: str
    data_pagamento: datetime
    # Add other relevant fields from PagamentoSchemas as needed
    class Config:
        from_attributes = True

class ComandaBase(BaseModel):
    # id_mesa: uuid.UUID # Mesa a que a comanda pertence, geralmente obrigatório na criação
    id_cliente_associado: Optional[uuid.UUID] = None
    # Outros campos que podem ser definidos na criação ou atualização
    observacoes: Optional[str] = Field(None, example="Comanda para grupo grande")

class ComandaCreate(ComandaBase):
    id_mesa: uuid.UUID # Obrigatório ao criar uma comanda para uma mesa
    pass

class ComandaUpdate(BaseModel):
    id_cliente_associado: Optional[uuid.UUID] = None
    status_pagamento: Optional[str] = Field(None, example="Parcialmente Paga") # e.g., Aberta, Fechada, Paga, Parcialmente Paga, Fiado
    observacoes: Optional[str] = Field(None, example="Cliente solicitou divisão da conta")
    # valor_total, valor_pago, valor_fiado são geralmente calculados e não diretamente atualizáveis aqui.

class Comanda(ComandaBase):
    id: uuid.UUID
    id_mesa: uuid.UUID # Referência à mesa
    valor_total: Decimal = Field(default=0.0)
    valor_pago: Decimal = Field(default=0.0)
    valor_fiado: Decimal = Field(default=0.0)
    status_pagamento: str = Field(..., example="Aberta") # e.g., Aberta, Fechada, Paga, Parcialmente Paga, Fiado
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    pedidos: List[Pedido] = [] # Using placeholder
    pagamentos: List[Pagamento] = [] # Using placeholder
    # cliente_associado: Optional[ClienteSchemas] = None # If displaying client details
    # mesa: Optional[MesaSchemas] = None # If displaying mesa details

    class Config:
        from_attributes = True


class ComandaDigital(BaseModel):
    id: uuid.UUID
    id_mesa: uuid.UUID
    status_pagamento: str
    valor_total: Decimal
    data_criacao: datetime
    pedidos: List[Pedido] = []

    class Config:
        from_attributes = True
