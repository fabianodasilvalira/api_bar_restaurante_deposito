# app/schemas/mesa.py
from typing import Optional, List
import uuid
from pydantic import BaseModel

from app.db.models.mesa import StatusMesa # Importar o Enum
from app.schemas.cliente import Cliente # Para exibir dados do cliente associado
# from app.schemas.comanda import Comanda # Para exibir a comanda ativa, se necessário

class MesaBase(BaseModel):
    numero_identificador: str
    capacidade: Optional[int] = None
    status: Optional[StatusMesa] = StatusMesa.DISPONIVEL
    id_cliente_associado: Optional[uuid.UUID] = None

class MesaCreate(MesaBase):
    pass

class MesaUpdate(BaseModel):
    numero_identificador: Optional[str] = None
    capacidade: Optional[int] = None
    status: Optional[StatusMesa] = None
    id_cliente_associado: Optional[uuid.UUID] = None
    # qr_code_hash não deve ser atualizável diretamente por aqui, é gerado internamente

class MesaInDBBase(MesaBase):
    id: uuid.UUID
    qr_code_hash: Optional[str] = None
    # data_criacao: datetime
    # data_atualizacao: Optional[datetime]

    class Config:
        from_attributes = True

class Mesa(MesaInDBBase):
    cliente_associado: Optional[Cliente] = None
    # comandas: List[Comanda] = [] # Para exibir comandas associadas, se necessário
    pass

# Schema para quando uma mesa é aberta e uma comanda é criada
class MesaComComandaInfo(Mesa):
    id_comanda_ativa: Optional[uuid.UUID] = None

