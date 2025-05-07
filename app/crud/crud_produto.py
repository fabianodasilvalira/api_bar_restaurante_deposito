# app/crud/crud_produto.py
from typing import List, Optional, Union, Dict, Any
import uuid
from sqlalchemy.orm import Session

from app.db.models.produto import Produto
from app.schemas.produto import ProdutoCreate, ProdutoUpdate

class CRUDProduto:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Produto]:
        return db.query(Produto).filter(Produto.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Produto]:
        return db.query(Produto).order_by(Produto.nome).offset(skip).limit(limit).all()
    
    def get_multi_by_categoria(
        self, db: Session, *, categoria: str, skip: int = 0, limit: int = 100
    ) -> List[Produto]:
        return db.query(Produto).filter(Produto.categoria == categoria).order_by(Produto.nome).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: ProdutoCreate) -> Produto:
        db_obj = Produto(
            nome=obj_in.nome,
            descricao=obj_in.descricao,
            preco_unitario=obj_in.preco_unitario,
            categoria=obj_in.categoria,
            disponivel=obj_in.disponivel if obj_in.disponivel is not None else True
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Produto, obj_in: Union[ProdutoUpdate, Dict[str, Any]]
    ) -> Produto:
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

    def remove(self, db: Session, *, id: uuid.UUID) -> Optional[Produto]:
        obj = db.query(Produto).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

produto = CRUDProduto()

