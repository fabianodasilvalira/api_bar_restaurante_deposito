# app/schemas/cliente.py
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr # EmailStr might not be needed for Cliente unless they have email

class ClienteBase(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None

class ClienteCreate(ClienteBase):
    # Telefone pode ser obrigatório na criação, dependendo dos requisitos
    # telefone: str
    pass

class ClienteUpdate(ClienteBase):
    pass

class ClienteInDBBase(ClienteBase):
    id: uuid.UUID
    # data_criacao: datetime # from Base model
    # data_atualizacao: Optional[datetime] = None # from Base model

    class Config:
        from_attributes = True

class Cliente(ClienteInDBBase):
    pass

