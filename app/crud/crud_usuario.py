# app/crud/crud_usuario.py
from typing import Any, Dict, Optional, Union, List
import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password # Assuming this path is correct
from app.models.usuario import Usuario # Corrected import path for the model
from app.schemas.usuario_schemas import UsuarioCreateSchemas, UsuarioUpdateSchemas # Corrected import path

class CRUDUsuario:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.id == id).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.email == email).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Usuario]:
        return db.query(Usuario).offset(skip).limit(limit).all()

    def create_user(self, db: Session, *, user_create: UsuarioCreateSchemas) -> Usuario:
        # Note: The original `create` method was here. Renaming to `create_user` for clarity
        # or ensuring the endpoint calls the correct CRUD method.
        # The original UsuarioCreateSchemas might not have `cargo`. This needs to be aligned.
        # For now, assuming UsuarioCreateSchemas has all necessary fields including password (not hashed).
        db_obj = Usuario(
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            nome_completo=user_create.nome_completo,
            # cargo=user_create.cargo, # Add if cargo is part of UsuarioCreateSchemas and Usuario model
            is_active=user_create.is_active if user_create.is_active is not None else True,
            is_superuser=user_create.is_superuser if hasattr(user_create, 'is_superuser') else False
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    # Alias for compatibility if other parts of code use `create`
    def create(self, db: Session, *, obj_in: UsuarioCreateSchemas) -> Usuario:
        return self.create_user(db=db, user_create=obj_in)

    def update(
        self, db: Session, *, db_obj: Usuario, obj_in: Union[UsuarioUpdateSchemas, Dict[str, Any]]
    ) -> Usuario:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        for field in update_data: # Itera sobre os campos fornecidos para atualização
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[Usuario]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: Usuario) -> bool:
        return user.is_active

    def is_superuser(self, user: Usuario) -> bool:
        return user.is_superuser

crud_usuario = CRUDUsuario() # Instantiated the class

