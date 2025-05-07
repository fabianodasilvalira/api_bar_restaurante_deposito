# app/crud/crud_pagamento.py
import uuid
from typing import List, Optional, Union, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.pagamento import Pagamento, MetodoPagamento, StatusPagamento
from app.db.models.comanda import Comanda, StatusComanda # Para atualizar status e valores da comanda
from app.db.models.fiado import Fiado # Para registrar fiado se o método for FIADO
from app.schemas.pagamento import PagamentoCreate
from app.crud.crud_comanda import comanda as crud_comanda # Para recalcular e atualizar comanda
# from app.crud.crud_fiado import fiado as crud_fiado # Para criar registro de fiado
# from app.services.redis_service import redis_client
# import json
# from datetime import datetime

class CRUDPagamento:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Pagamento]:
        return db.query(Pagamento).filter(Pagamento.id == id).first()

    def get_multi_by_comanda(self, db: Session, *, comanda_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Pagamento]:
        return db.query(Pagamento).filter(Pagamento.id_comanda == comanda_id).order_by(Pagamento.data_criacao.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: PagamentoCreate, id_usuario_registrou: Optional[uuid.UUID]) -> Pagamento:
        comanda_db = db.query(Comanda).filter(Comanda.id == obj_in.id_comanda).first()
        if not comanda_db:
            raise ValueError(f"Comanda com ID {obj_in.id_comanda} não encontrada.")

        if comanda_db.status_comanda not in [StatusComanda.FECHADA, StatusComanda.PAGA_PARCIALMENTE, StatusComanda.EM_FIADO, StatusComanda.ABERTA]:
            # Permitir pagamento em comanda ABERTA para pagamentos parciais antecipados
            raise ValueError(f"Não é possível registrar pagamento para uma comanda com status {comanda_db.status_comanda.value}")

        valor_a_pagar_na_comanda = comanda_db.valor_total_calculado - comanda_db.valor_pago - comanda_db.valor_fiado
        if obj_in.valor_pago <= Decimal("0"):
            raise ValueError("Valor do pagamento deve ser positivo.")
        
        # Não permitir pagar mais do que o valor restante, a menos que seja gorjeta (não modelado aqui)
        # if obj_in.valor_pago > valor_a_pagar_na_comanda and obj_in.metodo_pagamento != MetodoPagamento.FIADO:
        #     raise ValueError(f"Valor do pagamento (R$ {obj_in.valor_pago}) excede o valor restante da comanda (R$ {valor_a_pagar_na_comanda}).")

        db_pagamento = Pagamento(
            id_comanda=obj_in.id_comanda,
            id_cliente=obj_in.id_cliente or comanda_db.id_cliente_associado,
            id_usuario_registrou=id_usuario_registrou,
            valor_pago=obj_in.valor_pago,
            metodo_pagamento=obj_in.metodo_pagamento,
            status_pagamento=obj_in.status_pagamento or StatusPagamento.APROVADO,
            detalhes_transacao=obj_in.detalhes_transacao,
            observacoes=obj_in.observacoes
        )
        db.add(db_pagamento)
        
        # Atualizar valores na comanda
        if db_pagamento.status_pagamento == StatusPagamento.APROVADO:
            if obj_in.metodo_pagamento == MetodoPagamento.FIADO:
                # Se o método é FIADO, o valor_pago na comanda não aumenta, mas sim o valor_fiado
                comanda_db.valor_fiado += obj_in.valor_pago
                comanda_db.status_comanda = StatusComanda.EM_FIADO # Ou manter PAGA_PARCIALMENTE se houver outros pagamentos
                # Criar um registro de Fiado
                # fiado_obj_in = schemas.FiadoCreate(id_comanda=comanda_db.id, id_cliente=comanda_db.id_cliente_associado, valor=obj_in.valor_pago, observacoes=f"Registrado via pagamento ID: {db_pagamento.id}")
                # crud_fiado.create(db, obj_in=fiado_obj_in, id_usuario_registrou=id_usuario_registrou)
            else:
                comanda_db.valor_pago += obj_in.valor_pago

            # Verificar se a comanda foi totalmente paga
            if (comanda_db.valor_pago + comanda_db.valor_fiado) >= comanda_db.valor_total_calculado:
                comanda_db.status_comanda = StatusComanda.PAGA_TOTALMENTE
                # Se paga totalmente, a mesa pode ser liberada/fechada
                if comanda_db.mesa and comanda_db.mesa.status == StatusMesa.OCUPADA:
                    comanda_db.mesa.status = StatusMesa.FECHADA # Ou DISPONIVEL
                    db.add(comanda_db.mesa)
            elif comanda_db.valor_pago > Decimal("0") or comanda_db.valor_fiado > Decimal("0"):
                if comanda_db.status_comanda != StatusComanda.EM_FIADO:
                     comanda_db.status_comanda = StatusComanda.PAGA_PARCIALMENTE
            
            db.add(comanda_db)

        db.commit()
        db.refresh(db_pagamento)
        if comanda_db.status_comanda == StatusPagamento.APROVADO:
             db.refresh(comanda_db)

        # Publicar evento no Redis
        # redis_msg = {
        #     "evento": "novo_pagamento",
        #     "pagamento_id": str(db_pagamento.id),
        #     "comanda_id": str(comanda_db.id),
        #     "valor_pago": str(db_pagamento.valor_pago),
        #     "metodo": db_pagamento.metodo_pagamento.value,
        #     "status_comanda_novo": comanda_db.status_comanda.value,
        #     "timestamp": datetime.utcnow().isoformat()
        # }
        # await redis_client.publish_message(channel=f"comanda_{comanda_db.id}_pagamentos", message=json.dumps(redis_msg))

        return db_pagamento

    # Pagamentos geralmente não são removidos, mas cancelados (novo status)
    # def remove(self, db: Session, *, id: uuid.UUID) -> Optional[Pagamento]:
    #     obj = db.query(Pagamento).get(id)
    #     if obj:
    #         # Lógica para estornar valor na comanda se necessário
    #         db.delete(obj)
    #         db.commit()
    #     return obj

pagamento = CRUDPagamento()

