from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

# ✅ Import necessário para evitar o NameError
from app.schemas.comanda_schemas import Comanda

class MesaBase(BaseModel):
    numero_identificador: str = Field(..., example="M101")
    capacidade: Optional[int] = Field(None, example=4)
    status: Optional[str] = Field("Livre", example="Livre")
    localizacao: Optional[str] = Field(None, example="Salão Principal")

class MesaCreate(MesaBase):
    pass

class MesaUpdate(BaseModel):
    numero_identificador: Optional[str] = None
    capacidade: Optional[int] = None
    status: Optional[str] = None
    localizacao: Optional[str] = None

class Mesa(MesaBase):
    id: UUID

    class Config:
        from_attributes = True

class MesaComComandaInfo(Mesa):
    comanda: Optional[Comanda]

    class Config:
        from_attributes = True
