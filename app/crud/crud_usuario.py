# app/crud/crud_usuario.py
from typing import Any, Dict, Optional, Union, List
import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.db.models.usuario import Usuario # Ajuste o caminho se necessário
from app.schemas.usuario import UsuarioCreateSchemas, UsuarioUpdateSchemas # Ajuste o caminho se necessário

class CRUDUsuario:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.id == id).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.email == email).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Usuario]:
        return db.query(Usuario).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: UsuarioCreateSchemas) -> Usuario:
        db_obj = Usuario(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            nome_completo=obj_in.nome_completo,
            cargo=obj_in.cargo,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
            is_superuser=obj_in.is_superuser
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

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

usuario = CRUDUsuario()

