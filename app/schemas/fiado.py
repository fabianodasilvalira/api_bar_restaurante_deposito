# app/schemas/fiado.py
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime # Adicionado datetime para data_criacao, etc.

from pydantic import BaseModel

from app.db.models.fiado import StatusFiado # Importar Enum
from app.schemas.cliente import ClienteSchemas # Para exibir dados do cliente
from app.schemas.comanda import ComandaSchemas # Para exibir dados da comanda

class FiadoBaseSchemas(BaseModel):
    id_comanda: uuid.UUID
    id_cliente: uuid.UUID
    valor_original: Decimal
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None

class FiadoCreateSchemas(FiadoBaseSchemas):
    # valor_devido e status_fiado serão definidos no backend na criação
    pass

class FiadoUpdateSchemas(BaseModel):
    # Usado para registrar um pagamento no fiado ou alterar status/observações
    valor_pago_neste_momento: Optional[Decimal] = None # Se um pagamento está sendo feito para este fiado
    status_fiado: Optional[StatusFiado] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None

class FiadoInDBBaseSchemas(FiadoBaseSchemas):
    id: uuid.UUID
    id_usuario_registrou: Optional[uuid.UUID] = None
    valor_devido: Decimal
    status_fiado: StatusFiado
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class FiadoSchemas(FiadoInDBBaseSchemas):
    cliente: Optional[ClienteSchemas] = None
    comanda: Optional[ComandaSchemas] = None # Simplificado, pode não precisar de todos os detalhes da comanda aqui
    pass

# Schema para relatórios de fiado (já definido anteriormente, mas pode ser referenciado ou ajustado aqui)
# from app.schemas.relatorio import RelatorioFiadoItem, RelatorioFiado # Se movido para cá

