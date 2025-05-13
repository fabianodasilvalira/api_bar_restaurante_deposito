# app/schemas/cliente_schemas.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class ClienteBase(BaseModel):
    nome: str = Field(..., example="João da Silva")
    telefone: Optional[str] = Field(None, example="(11) 99999-8888")
    email: Optional[EmailStr] = Field(None, example="joao.silva@example.com")
    observacoes: Optional[str] = Field(None, example="Cliente VIP, prefere mesa perto da janela.")

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    observacoes: Optional[str] = None

class Cliente(ClienteBase):
    id: UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True

