# app/schemas/usuario_schemas.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UsuarioBaseSchemas(BaseModel):
    email: EmailStr = Field(..., example="usuario@exemplo.com")
    nome_completo: Optional[str] = Field(None, example="Nome Completo do Usuário")
    is_active: Optional[bool] = True
    is_superuser: bool = False
    cargo: Optional[str] = Field(None, example="Garçom") # Ex: Garçom, Caixa, Gerente

class UsuarioCreateSchemas(UsuarioBaseSchemas):
    password: str = Field(..., min_length=8, example="senhaForte123")

class UsuarioUpdateSchemas(BaseModel):
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    cargo: Optional[str] = None

class UsuarioInDBBaseSchemas(UsuarioBaseSchemas):
    id: UUID
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True # Changed from orm_mode = True for Pydantic v2

# Adicional para visualização (sem o Hashed Password)
class UsuarioSchemas(UsuarioInDBBaseSchemas):
    pass

