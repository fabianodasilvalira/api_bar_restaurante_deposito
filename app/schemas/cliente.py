# app/schemas/cliente.py
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr # EmailStr might not be needed for Cliente unless they have email

class ClienteBaseSchemas(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None

class ClienteCreateSchemas(ClienteBaseSchemas):
    # Telefone pode ser obrigatório na criação, dependendo dos requisitos
    # telefone: str
    pass

class ClienteUpdateSchemas(ClienteBaseSchemas):
    pass

class ClienteInDBBaseSchemas(ClienteBaseSchemas):
    id: uuid.UUID
    # data_criacao: datetime # from Base model
    # data_atualizacao: Optional[datetime] = None # from Base model

    class Config:
        from_attributes = True

class ClienteSchemas(ClienteInDBBaseSchemas):
    pass

