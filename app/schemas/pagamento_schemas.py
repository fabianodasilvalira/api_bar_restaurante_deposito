# app/schemas/pagamento_schemas.py
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class PagamentoBase(BaseModel):
    comanda_id: UUID
    valor: Decimal = Field(..., gt=0, example=50.75)
    metodo_pagamento: str = Field(..., example="Cartão de Crédito") # Ex: Dinheiro, Cartão Crédito, Cartão Débito, Pix
    observacoes: Optional[str] = Field(None, example="Pagamento parcial da comanda.")

class PagamentoCreate(PagamentoBase):
    pass

# Geralmente pagamentos não são atualizados, mas registrados e, se necessário, estornados/cancelados.
# Manter um PagamentoUpdate pode ser útil para casos específicos, como adicionar uma observação posterior.
class PagamentoUpdate(BaseModel):
    observacoes: Optional[str] = None
    # Outros campos que poderiam ser atualizados, se a lógica de negócio permitir.
    # Por exemplo, se um pagamento foi registrado com o método errado e precisa ser corrigido:
    # metodo_pagamento: Optional[str] = None 

class Pagamento(PagamentoBase):
    id: UUID
    data_pagamento: datetime
    id_usuario_registrou: Optional[UUID] = None # ID do usuário (caixa/garçom) que registrou o pagamento

    class Config:
        from_attributes = True

