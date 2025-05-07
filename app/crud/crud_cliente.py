# app/crud/crud_cliente.py
from typing import List, Optional, Union, Dict, Any
import uuid
from sqlalchemy.orm import Session

from app.db.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate

class CRUDCliente:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Cliente]:
        return db.query(Cliente).filter(Cliente.id == id).first()

    def get_by_telefone(self, db: Session, *, telefone: str) -> Optional[Cliente]:
        return db.query(Cliente).filter(Cliente.telefone == telefone).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Cliente]:
        return db.query(Cliente).order_by(Cliente.nome).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: ClienteCreate) -> Cliente:
        db_obj = Cliente(
            nome=obj_in.nome,
            telefone=obj_in.telefone,
            observacoes=obj_in.observacoes
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Cliente, obj_in: Union[ClienteUpdate, Dict[str, Any]]
    ) -> Cliente:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: uuid.UUID) -> Optional[Cliente]:
        obj = db.query(Cliente).get(id)
        if obj:
            # Adicionar lógica aqui para verificar se o cliente tem fiados pendentes antes de remover
            # if obj.comandas_fiado and any(fiado.status != "Pago Totalmente" for fiado in obj.comandas_fiado):
            #     raise ValueError("Cliente possui fiados pendentes e não pode ser removido.")
            db.delete(obj)
            db.commit()
        return obj

cliente = CRUDCliente()

