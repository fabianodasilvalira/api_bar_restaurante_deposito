# app/schemas/pagamento.py
import uuid
from typing import Optional
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel

from app.db.models.pagamento import MetodoPagamento, StatusPagamento # Importar Enums
# from app.schemas.cliente import Cliente # Para exibir dados do cliente
# from app.schemas.usuario import Usuario # Para exibir dados do usuário

class PagamentoBaseSchemas(BaseModel):
    id_comanda: uuid.UUID
    id_cliente: Optional[uuid.UUID] = None
    valor_pago: Decimal
    metodo_pagamento: MetodoPagamento
    status_pagamento: Optional[StatusPagamento] = StatusPagamento.APROVADO
    detalhes_transacao: Optional[str] = None
    observacoes: Optional[str] = None

class PagamentoCreateSchemas(PagamentoBaseSchemas):
    pass

# Pagamentos geralmente não são atualizados, um novo é criado ou um é cancelado.
# class PagamentoUpdateSchemas(BaseModel):
#     status_pagamento: Optional[StatusPagamento] = None
#     observacoes: Optional[str] = None

class PagamentoInDBBaseSchemas(PagamentoBaseSchemas):
    id: uuid.UUID
    id_usuario_registrou: Optional[uuid.UUID] = None
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class PagamentoSchemas(PagamentoInDBBaseSchemas):
    # cliente: Optional[Cliente] = None
    # usuario_registrou: Optional[Usuario] = None
    pass

