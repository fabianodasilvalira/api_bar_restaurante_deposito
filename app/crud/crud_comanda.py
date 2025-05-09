# app/crud/crud_comanda.py
import uuid
from typing import List, Optional, Union, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.db.models.comanda import Comanda, StatusComanda
from app.db.models.mesa import Mesa, StatusMesa # Para atualizar status da mesa
from app.schemas.comanda import ComandaCreateSchemas, ComandaUpdateSchemas
# from app.services.redis_service import redis_client # Para publicar eventos
# import json

class CRUDComanda:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Comanda]:
        return db.query(Comanda).filter(Comanda.id == id).first()

    def get_comanda_ativa_by_mesa(self, db: Session, *, mesa_id: uuid.UUID) -> Optional[Comanda]:
        """Retorna a comanda ativa (Aberta ou Paga Parcialmente) para uma mesa."""
        return db.query(Comanda).filter(
            Comanda.id_mesa == mesa_id,
            Comanda.status_comanda.in_([StatusComanda.ABERTA, StatusComanda.PAGA_PARCIALMENTE, StatusComanda.EM_FIADO])
        ).order_by(Comanda.data_criacao.desc()).first()

    def get_multi_by_mesa(self, db: Session, *, mesa_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Comanda]:
        return db.query(Comanda).filter(Comanda.id_mesa == mesa_id).order_by(Comanda.data_criacao.desc()).offset(skip).limit(limit).all()

    def get_multi_by_cliente(self, db: Session, *, cliente_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Comanda]:
        return db.query(Comanda).filter(Comanda.id_cliente_associado == cliente_id).order_by(Comanda.data_criacao.desc()).offset(skip).limit(limit).all()

    def create_comanda_para_mesa(self, db: Session, *, mesa_id: uuid.UUID, id_cliente_associado: Optional[uuid.UUID] = None) -> Comanda:
        """
        Cria uma nova comanda para uma mesa. 
        Esta função é chamada quando uma mesa é aberta.
        """
        # Verificar se já existe uma comanda ativa para esta mesa
        comanda_ativa_existente = self.get_comanda_ativa_by_mesa(db, mesa_id=mesa_id)
        if comanda_ativa_existente:
            # Poderia retornar a existente ou levantar um erro, dependendo da regra de negócio.
            # Por ora, vamos permitir criar uma nova se a mesa for reaberta, mas a lógica de abrir mesa deve tratar isso.
            # raise ValueError(f"Mesa {mesa_id} já possui uma comanda ativa (ID: {comanda_ativa_existente.id}).")
            pass # A lógica de abrir mesa no crud_mesa já deve ter mudado o status da mesa.

        obj_in_data = {"id_mesa": mesa_id, "id_cliente_associado": id_cliente_associado}
        db_obj = Comanda(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Atualizar status da mesa para OCUPADA, se não estiver
        mesa = db.query(Mesa).filter(Mesa.id == mesa_id).first()
        if mesa and mesa.status != StatusMesa.OCUPADA:
            mesa.status = StatusMesa.OCUPADA
            if id_cliente_associado and not mesa.id_cliente_associado:
                 mesa.id_cliente_associado = id_cliente_associado
            db.add(mesa)
            db.commit()

        # Publicar evento no Redis
        # await redis_client.publish_message(f"mesa_{mesa_id}_comandas", json.dumps({"evento": "comanda_criada", "comanda_id": str(db_obj.id)}))
        return db_obj

    def update(self, db: Session, *, db_obj: Comanda, obj_in: Union[ComandaUpdateSchemas, Dict[str, Any]]) -> Comanda:
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
        # Publicar evento no Redis se o status da comanda mudar
        # if "status_comanda" in update_data:
        #     await redis_client.publish_message(f"comanda_{db_obj.id}_status", json.dumps({"status": db_obj.status_comanda.value}))
        return db_obj

    def recalcular_total_comanda(self, db: Session, *, comanda_id: uuid.UUID) -> Comanda:
        comanda = self.get(db, id=comanda_id)
        if not comanda:
            raise ValueError("Comanda não encontrada para recalcular totais.")

        total_itens = db.query(func.sum(func.coalesce(ItemPedido.preco_total_item, Decimal("0.00")))).filter(ItemPedido.id_comanda == comanda_id).scalar() or Decimal("0.00")
        # total_pago já é atualizado via pagamentos
        # total_fiado já é atualizado via fiados
        
        comanda.valor_total_calculado = total_itens
        # O valor restante é (valor_total_calculado - valor_pago - valor_fiado)
        # A lógica de fechar comanda ou registrar fiado deve garantir consistência.

        db.add(comanda)
        db.commit()
        db.refresh(comanda)
        # Publicar atualização de valores no Redis
        # await redis_client.publish_message(f"comanda_{comanda.id}_valores", json.dumps({
        #     "total_calculado": str(comanda.valor_total_calculado),
        #     "valor_pago": str(comanda.valor_pago),
        #     "valor_fiado": str(comanda.valor_fiado)
        # }))
        return comanda

    def fechar_comanda_para_pagamento(self, db: Session, *, comanda_id: uuid.UUID) -> Comanda:
        comanda = self.get(db, id=comanda_id)
        if not comanda:
            raise ValueError("Comanda não encontrada.")
        if comanda.status_comanda != StatusComanda.ABERTA:
            raise ValueError(f"Comanda não está aberta (status atual: {comanda.status_comanda}).")
        
        comanda = self.recalcular_total_comanda(db, comanda_id=comanda_id)
        comanda.status_comanda = StatusComanda.FECHADA
        db.add(comanda)
        db.commit()
        db.refresh(comanda)
        # Publicar no Redis
        return comanda

    # Outras funções CRUD (get_multi, delete se necessário) podem ser adicionadas.
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: Optional[StatusComanda] = None
    ) -> List[Comanda]:
        query = db.query(Comanda)
        if status:
            query = query.filter(Comanda.status_comanda == status)
        return query.order_by(Comanda.data_criacao.desc()).offset(skip).limit(limit).all()

comanda = CRUDComanda()

# É preciso importar ItemPedido para a função recalcular_total_comanda
from app.db.models.pedido import ItemPedido
