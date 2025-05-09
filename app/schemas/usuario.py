# app/schemas/usuario.py
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr

# Propriedades compartilhadas que todos os schemas de usuário terão
class UsuarioBaseSchemas(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    nome_completo: Optional[str] = None
    cargo: Optional[str] = None

# Propriedades para receber na criação do usuário via API
class UsuarioCreateSchemas(UsuarioBaseSchemas):
    email: EmailStr
    password: str

# Propriedades para receber na atualização do usuário via API
class UsuarioUpdateSchemas(UsuarioBaseSchemas):
    password: Optional[str] = None

# Propriedades armazenadas no DB que podem ser retornadas pela API
class UsuarioInDBBaseSchemas(UsuarioBaseSchemas):
    id: uuid.UUID
    # data_criacao: datetime # Herdados da Base Model, mas Pydantic precisa saber
    # data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True # Antigo orm_mode = True

# Propriedades adicionais para retornar via API
class UsuarioSchemas(UsuarioInDBBaseSchemas):
    pass

# Propriedades adicionais armazenadas no DB
class UsuarioInDBSchemas(UsuarioInDBBaseSchemas):
    hashed_password: str

