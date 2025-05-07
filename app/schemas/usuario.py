# app/schemas/usuario.py
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr

# Propriedades compartilhadas que todos os schemas de usuário terão
class UsuarioBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    nome_completo: Optional[str] = None
    cargo: Optional[str] = None

# Propriedades para receber na criação do usuário via API
class UsuarioCreate(UsuarioBase):
    email: EmailStr
    password: str

# Propriedades para receber na atualização do usuário via API
class UsuarioUpdate(UsuarioBase):
    password: Optional[str] = None

# Propriedades armazenadas no DB que podem ser retornadas pela API
class UsuarioInDBBase(UsuarioBase):
    id: uuid.UUID
    # data_criacao: datetime # Herdados da Base Model, mas Pydantic precisa saber
    # data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True # Antigo orm_mode = True

# Propriedades adicionais para retornar via API
class Usuario(UsuarioInDBBase):
    pass

# Propriedades adicionais armazenadas no DB
class UsuarioInDB(UsuarioInDBBase):
    hashed_password: str

