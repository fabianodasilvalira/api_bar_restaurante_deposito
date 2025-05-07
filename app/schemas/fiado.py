# app/schemas/fiado.py
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime # Adicionado datetime para data_criacao, etc.

from pydantic import BaseModel

from app.db.models.fiado import StatusFiado # Importar Enum
from app.schemas.cliente import Cliente # Para exibir dados do cliente
from app.schemas.comanda import Comanda # Para exibir dados da comanda

class FiadoBase(BaseModel):
    id_comanda: uuid.UUID
    id_cliente: uuid.UUID
    valor_original: Decimal
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None

class FiadoCreate(FiadoBase):
    # valor_devido e status_fiado serão definidos no backend na criação
    pass

class FiadoUpdate(BaseModel):
    # Usado para registrar um pagamento no fiado ou alterar status/observações
    valor_pago_neste_momento: Optional[Decimal] = None # Se um pagamento está sendo feito para este fiado
    status_fiado: Optional[StatusFiado] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None

class FiadoInDBBase(FiadoBase):
    id: uuid.UUID
    id_usuario_registrou: Optional[uuid.UUID] = None
    valor_devido: Decimal
    status_fiado: StatusFiado
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

class Fiado(FiadoInDBBase):
    cliente: Optional[Cliente] = None
    comanda: Optional[Comanda] = None # Simplificado, pode não precisar de todos os detalhes da comanda aqui
    pass

# Schema para relatórios de fiado (já definido anteriormente, mas pode ser referenciado ou ajustado aqui)
# from app.schemas.relatorio import RelatorioFiadoItem, RelatorioFiado # Se movido para cá

