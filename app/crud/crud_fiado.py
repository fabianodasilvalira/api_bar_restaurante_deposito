# app/crud/crud_fiado.py
import uuid
from typing import List, Optional, Union, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import date, timedelta # Para relatórios

from app.db.models.fiado import Fiado, StatusFiado
from app.db.models.comanda import Comanda, StatusComanda # Para atualizar status da comanda
from app.db.models.cliente import Cliente # Para relatório
from app.schemas.fiado import FiadoCreate, FiadoUpdate
from app.schemas.relatorio import RelatorioFiado, RelatorioFiadoItem # Para o relatório
# from app.services.redis_service import redis_client
# import json
# from datetime import datetime

class CRUDFiado:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Fiado]:
        return db.query(Fiado).filter(Fiado.id == id).first()

    def get_multi_by_comanda(self, db: Session, *, comanda_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Fiado]:
        return db.query(Fiado).filter(Fiado.id_comanda == comanda_id).order_by(Fiado.data_criacao.desc()).offset(skip).limit(limit).all()

    def get_multi_by_cliente(
        self, db: Session, *, cliente_id: uuid.UUID, status: Optional[StatusFiado] = None, skip: int = 0, limit: int = 100
    ) -> List[Fiado]:
        query = db.query(Fiado).filter(Fiado.id_cliente == cliente_id)
        if status:
            query = query.filter(Fiado.status_fiado == status)
        return query.order_by(Fiado.data_criacao.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: FiadoCreate, id_usuario_registrou: Optional[uuid.UUID]) -> Fiado:
        comanda_db = db.query(Comanda).filter(Comanda.id == obj_in.id_comanda).first()
        if not comanda_db:
            raise ValueError(f"Comanda com ID {obj_in.id_comanda} não encontrada.")
        
        cliente_db = db.query(Cliente).filter(Cliente.id == obj_in.id_cliente).first()
        if not cliente_db:
            raise ValueError(f"Cliente com ID {obj_in.id_cliente} não encontrado.")

        if obj_in.valor_original <= Decimal("0"):
            raise ValueError("Valor original do fiado deve ser positivo.")

        # Verificar se o valor do fiado não excede o que falta na comanda
        valor_restante_comanda = comanda_db.valor_total_calculado - comanda_db.valor_pago - comanda_db.valor_fiado
        if obj_in.valor_original > valor_restante_comanda:
            # Permitir registrar fiado maior que o restante se for um novo fiado, mas ajustar o valor_fiado da comanda
            # Ou lançar erro. Por ora, vamos permitir, mas a comanda será atualizada.
            pass 

        db_fiado = Fiado(
            id_comanda=obj_in.id_comanda,
            id_cliente=obj_in.id_cliente,
            id_usuario_registrou=id_usuario_registrou,
            valor_original=obj_in.valor_original,
            valor_devido=obj_in.valor_original, # Inicialmente, valor devido é o valor total
            status_fiado=StatusFiado.PENDENTE,
            data_vencimento=obj_in.data_vencimento,
            observacoes=obj_in.observacoes
        )
        db.add(db_fiado)

        # Atualizar valor_fiado e status da comanda
        comanda_db.valor_fiado += obj_in.valor_original
        if comanda_db.status_comanda != StatusComanda.EM_FIADO:
            # Se já estava PAGA_PARCIALMENTE ou ABERTA, e agora tem fiado, muda para EM_FIADO
            # Se estava FECHADA e registrou fiado, também muda para EM_FIADO
            comanda_db.status_comanda = StatusComanda.EM_FIADO
        
        # Verificar se a comanda foi totalmente coberta (pago + fiado)
        if (comanda_db.valor_pago + comanda_db.valor_fiado) >= comanda_db.valor_total_calculado:
            if comanda_db.valor_pago < comanda_db.valor_total_calculado: # Ainda tem saldo devedor no fiado
                 comanda_db.status_comanda = StatusComanda.EM_FIADO
            else: # Tudo pago, nada no fiado (caso raro se chegou aqui)
                 comanda_db.status_comanda = StatusComanda.PAGA_TOTALMENTE
            
            if comanda_db.status_comanda == StatusComanda.PAGA_TOTALMENTE and comanda_db.mesa:
                if comanda_db.mesa.status == StatusMesa.OCUPADA:
                    comanda_db.mesa.status = StatusMesa.FECHADA
                    db.add(comanda_db.mesa)
        db.add(comanda_db)

        db.commit()
        db.refresh(db_fiado)
        db.refresh(comanda_db)

        # Publicar evento no Redis
        # redis_msg = {
        #     "evento": "novo_fiado",
        #     "fiado_id": str(db_fiado.id),
        #     "comanda_id": str(comanda_db.id),
        #     "cliente_id": str(db_fiado.id_cliente),
        #     "valor": str(db_fiado.valor_original),
        #     "timestamp": datetime.utcnow().isoformat()
        # }
        # await redis_client.publish_message(channel=f"cliente_{db_fiado.id_cliente}_fiados", message=json.dumps(redis_msg))
        return db_fiado

    def registrar_pagamento_fiado(self, db: Session, *, fiado_id: uuid.UUID, valor_pago: Decimal, id_usuario_registrou: Optional[uuid.UUID]) -> Optional[Fiado]:
        fiado_db = self.get(db, id=fiado_id)
        if not fiado_db:
            return None
        
        if valor_pago <= Decimal("0"):
            raise ValueError("Valor do pagamento do fiado deve ser positivo.")
        if valor_pago > fiado_db.valor_devido:
            raise ValueError(f"Valor pago (R$ {valor_pago}) excede o valor devido (R$ {fiado_db.valor_devido}) para este fiado.")

        fiado_db.valor_devido -= valor_pago
        
        # Atualizar status do fiado
        if fiado_db.valor_devido <= Decimal("0"):
            fiado_db.status_fiado = StatusFiado.PAGO_TOTALMENTE
            fiado_db.valor_devido = Decimal("0") # Garantir que não fique negativo
        else:
            fiado_db.status_fiado = StatusFiado.PAGO_PARCIALMENTE
        
        db.add(fiado_db)

        # Atualizar comanda associada (valor_pago na comanda aumenta, valor_fiado na comanda diminui)
        comanda_db = fiado_db.comanda
        if comanda_db:
            comanda_db.valor_pago += valor_pago # O pagamento do fiado é um pagamento "real" na comanda
            # O valor_fiado da comanda representa o total que *foi* para fiado, não o saldo atual de todos os fiados.
            # A baixa do fiado individual não reduz o `comanda.valor_fiado` diretamente, mas sim o `fiado.valor_devido`.
            # A comanda é considerada quitada quando (valor_pago + valor_fiado_original_registrado) >= valor_total_calculado
            # E todos os `fiado.valor_devido` associados a ela são zero.

            if fiado_db.status_fiado == StatusFiado.PAGO_TOTALMENTE:
                # Verificar se todos os fiados desta comanda estão pagos para mudar status da comanda
                todos_fiados_pagos = True
                for f in comanda_db.fiados_registrados:
                    if f.status_fiado not in [StatusFiado.PAGO_TOTALMENTE, StatusFiado.CANCELADO]:
                        todos_fiados_pagos = False
                        break
                if todos_fiados_pagos and (comanda_db.valor_pago >= comanda_db.valor_total_calculado):
                    comanda_db.status_comanda = StatusComanda.PAGA_TOTALMENTE
                    if comanda_db.mesa and comanda_db.mesa.status == StatusMesa.OCUPADA:
                        comanda_db.mesa.status = StatusMesa.FECHADA
                        db.add(comanda_db.mesa)
                elif comanda_db.status_comanda == StatusComanda.EM_FIADO: # Se ainda há outros fiados pendentes
                    pass # Mantém EM_FIADO
            db.add(comanda_db)

        db.commit()
        db.refresh(fiado_db)
        if comanda_db: db.refresh(comanda_db)

        # Publicar evento no Redis
        return fiado_db

    def update(self, db: Session, *, db_obj: Fiado, obj_in: Union[FiadoUpdate, Dict[str, Any]]) -> Fiado:
        # Esta função é mais para atualizar dados como observações, data_vencimento ou status manualmente.
        # Pagamentos devem usar `registrar_pagamento_fiado`.
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if "valor_pago_neste_momento" in update_data and update_data["valor_pago_neste_momento"]:
            # Isso deveria ir para registrar_pagamento_fiado
            raise ValueError("Para registrar pagamento em fiado, use o endpoint específico.")

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_relatorio_fiado(self, db: Session, data_inicio: date, data_fim: date) -> RelatorioFiado:
        # Esta é a lógica que estava no main.py da entrega anterior, adaptada.
        # Fiados pendentes ou parcialmente pagos criados no período ou que ainda estavam pendentes no início do período
        # Ou que se tornaram pendentes/parciais dentro do período.
        # A consulta precisa ser refinada para o que o usuário realmente quer ver: Saldo devedor no final do período? Movimentação?
        # Assumindo saldo devedor de fiados que estão ABERTOS (Pendente ou Pago Parcialmente) no final do período `data_fim`,
        # e que foram criados em qualquer momento até `data_fim`.
        
        # Fiados que estão com status Pendente ou Pago Parcialmente no final do período.
        fiados_abertos_no_final_periodo = db.query(
            Fiado.id_cliente,
            Cliente.nome.label("nome_cliente"),
            func.sum(Fiado.valor_devido).label("valor_total_devido_cliente"),
            func.count(Fiado.id).label("quantidade_fiados_pendentes_cliente")
        ).join(Cliente, Fiado.id_cliente == Cliente.id)
        .filter(
            Fiado.status_fiado.in_([StatusFiado.PENDENTE, StatusFiado.PAGO_PARCIALMENTE]),
            Fiado.data_criacao <= data_fim # Considera todos criados até o fim do período
            # Se quiser apenas os que *ainda estavam abertos* no fim do período, a data_criacao é suficiente
            # Se quiser os que *movimentaram* no período, a lógica é mais complexa.
        ).group_by(Fiado.id_cliente, Cliente.nome).all()

        detalhes_clientes = []
        total_geral_devido_calculado = Decimal("0.0")
        
        for fiado_info in fiados_abertos_no_final_periodo:
            if fiado_info.valor_total_devido_cliente > Decimal("0"):
                detalhes_clientes.append(RelatorioFiadoItem(
                    id_cliente=fiado_info.id_cliente,
                    nome_cliente=fiado_info.nome_cliente or "Cliente não informado",
                    valor_total_devido=fiado_info.valor_total_devido_cliente,
                    quantidade_fiados_pendentes=fiado_info.quantidade_fiados_pendentes_cliente
                ))
                total_geral_devido_calculado += fiado_info.valor_total_devido_cliente

        # Contar total de registros de fiado (Pendente/Parcial) que se enquadram no critério do relatório.
        # Este count pode ser o número de clientes com saldo ou o número de transações de fiado em aberto.
        # A query acima já agrupa por cliente, então len(detalhes_clientes) seria o número de clientes com saldo.
        # Se for o número de *transações* de fiado em aberto:
        count_total_transacoes_fiado_abertas = db.query(func.count(Fiado.id)).filter(
            Fiado.status_fiado.in_([StatusFiado.PENDENTE, StatusFiado.PAGO_PARCIALMENTE]),
            Fiado.data_criacao <= data_fim
        ).scalar() or 0

        return RelatorioFiado(
            periodo_inicio=data_inicio, # O relatório é de saldo *em* data_fim, mas o período é informativo.
            periodo_fim=data_fim,
            total_geral_devido=total_geral_devido_calculado,
            total_fiados_registrados_periodo=count_total_transacoes_fiado_abertas, # Ou len(detalhes_clientes) se for por cliente
            detalhes_por_cliente=detalhes_clientes
        )

fiado = CRUDFiado()

