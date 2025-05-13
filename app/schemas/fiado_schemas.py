# app/schemas/fiado_schemas.py
from typing import Optional
import uuid
from datetime import datetime, date # Added date for data_vencimento
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

# Definindo o Enum StatusFiado
class StatusFiado(Enum):
    PENDENTE = "Pendente"
    PAGO = "Pago"
    VENCIDO = "Vencido"
    RENEGOCIADO = "Renegociado"


class Cliente(BaseModel): # Placeholder
    id: uuid.UUID
    nome: Optional[str] = None
    class Config:
        from_attributes = True

class Comanda(BaseModel): # Placeholder
    id: uuid.UUID
    # Add other relevant fields from ComandaSchemas if needed
    class Config:
        from_attributes = True

class FiadoBaseSchemas(BaseModel):
    id_cliente: uuid.UUID
    valor_devido: Decimal = Field(..., gt=0)
    data_vencimento: Optional[date] = None # Changed to date as time is not usually relevant for due date
    status: Optional[str] = Field("Pendente", example="Pendente") # Pendente, Pago, Vencido, Renegociado
    observacoes: Optional[str] = Field(None, example="Cliente pagará na próxima semana")

class FiadoCreateSchemas(FiadoBaseSchemas):
    id_comanda_origem: uuid.UUID

class FiadoUpdateSchemas(BaseModel):
    valor_devido: Optional[Decimal] = Field(None, gt=0)
    data_vencimento: Optional[date] = None
    status: Optional[str] = Field(None, example="Pago")
    observacoes: Optional[str] = Field(None, example="Pagamento realizado integralmente")

class FiadoSchemas(FiadoBaseSchemas):
    id: uuid.UUID
    id_comanda_origem: uuid.UUID
    data_criacao: datetime
    data_ultima_atualizacao: Optional[datetime] = None

    cliente: Cliente # Placeholder
    comanda_origem: Comanda # Placeholder

    class Config:
        from_attributes = True


class FiadoCreateSchemas(FiadoBaseSchemas):
    id_comanda_origem: uuid.UUID


