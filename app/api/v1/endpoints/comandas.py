# app/api/v1/endpoints/comandas.py
import uuid
from decimal import Decimal
from typing import List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.schemas.comanda_schemas import StatusComanda # Importar o Enum

from app.models.usuario import Usuario
from app.schemas.comanda_schemas import ComandaDigital

# from app.services.redis_service import redis_client # Para publicar eventos no Redis
# import json # Para formatar mensagens Redis

router = APIRouter()

# Não haverá um endpoint para criar comanda diretamente por aqui.
# A comanda é criada automaticamente ao ABRIR UMA MESA (ver endpoint em mesas.py).
# Ou quando um pedido de DELIVERY é iniciado (lógica a ser adicionada se delivery for um fluxo separado de comanda de mesa).

@router.get("/", response_model=List[schemas.Comanda])
def read_comandas(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    status_comanda: Optional[StatusComanda] = None,
    id_mesa: Optional[uuid.UUID] = None,
    id_cliente: Optional[uuid.UUID] = None,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera a lista de comandas. Pode ser filtrada por status, mesa ou cliente.
    """
    if id_mesa:
        comandas = crud.comanda.get_multi_by_mesa(db, mesa_id=id_mesa, skip=skip, limit=limit)
    elif id_cliente:
        comandas = crud.comanda.get_multi_by_cliente(db, cliente_id=id_cliente, skip=skip, limit=limit)
    else:
        comandas = crud.comanda.get_multi(db, skip=skip, limit=limit, status=status_comanda)
    return comandas

@router.get("/{comanda_id}", response_model=schemas.Comanda)
def read_comanda_by_id(
    comanda_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user) # Acesso restrito
) -> Any:
    """
    Recupera uma comanda pelo seu ID.
    """
    comanda = crud.comanda.get(db=db, id=comanda_id)
    if not comanda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda não encontrada")
    return comanda

@router.put("/{comanda_id}", response_model=schemas.Comanda)
def update_comanda(
    *,
    db: Session = Depends(deps.get_db),
    comanda_id: uuid.UUID,
    comanda_in: schemas.ComandaUpdate,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Atualiza uma comanda (ex: status, observações).
    Outras atualizações (valores) são feitas por lógicas de pedido/pagamento.
    """
    comanda = crud.comanda.get(db=db, id=comanda_id)
    if not comanda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda não encontrada")

    # Lógica de transição de status pode ser mais complexa e ficar no CRUD ou serviço
    comanda = crud.comanda.update(db=db, db_obj=comanda, obj_in=comanda_in)

    # Publicar evento no Redis se o status da comanda mudar
    # if comanda_in.status_comanda:
    #     await redis_client.publish_message(f"comanda_{comanda.id}_status", json.dumps({"status": comanda.status_comanda.value}))
    return comanda

@router.post("/{comanda_id}/solicitar-fechamento", response_model=schemas.Comanda)
def solicitar_fechamento_comanda(
    comanda_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user) # Garçom ou cliente (se autenticado)
) -> Any:
    """
    Cliente ou garçom solicita o fechamento da comanda para pagamento.
    A comanda é recalculada e seu status muda para FECHADA.
    """
    try:
        comanda = crud.comanda.fechar_comanda_para_pagamento(db=db, comanda_id=comanda_id)
        # Notificar via Redis que a comanda foi fechada e está pronta para pagamento
        # await redis_client.publish_message(f"comanda_{comanda.id}_eventos", json.dumps({"evento": "solicitacao_fechamento", "status": comanda.status_comanda.value}))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return comanda

# Endpoint para o cliente visualizar a comanda digital (via QR Code hash)
# Este endpoint deve ser público ou ter uma forma de autenticação leve para o cliente.
@router.get("/digital/{qr_code_hash}", response_model=ComandaDigital) # Ajustar response_model para o que o cliente vê
def get_comanda_digital_via_qr(
    qr_code_hash: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Endpoint público para o cliente visualizar sua comanda via QR Code.
    """
    mesa = crud.mesa.get_by_qr_code_hash(db, qr_code_hash=qr_code_hash)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR Code inválido ou mesa não encontrada.")
    
    comanda_ativa = crud.comanda.get_comanda_ativa_by_mesa(db, mesa_id=mesa.id)
    if not comanda_ativa:
        # Se a mesa estiver ocupada mas sem comanda ativa, pode ser um estado de erro ou a mesa acabou de ser aberta
        # Poderia retornar um status indicando para aguardar ou contatar o garçom.
        # Por ora, se não há comanda ativa, não há o que mostrar.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma comanda ativa encontrada para esta mesa.")

    # Calcular valor restante
    valor_restante = comanda_ativa.valor_total_calculado - comanda_ativa.valor_pago - comanda_ativa.valor_fiado
    if valor_restante < 0: valor_restante = Decimal("0.00")

    # Montar o schema de ComandaDigital
    # Precisaria de um schema ItemPedidoComandaDigital e buscar os itens.
    # Por simplicidade, vamos omitir os itens detalhados por agora.
    comanda_digital_data = schemas.ComandaDigital(
        id=comanda_ativa.id,
        numero_mesa=mesa.numero_identificador,
        status_comanda=comanda_ativa.status_comanda,
        valor_total_calculado=comanda_ativa.valor_total_calculado,
        valor_pago=comanda_ativa.valor_pago,
        valor_restante=valor_restante,
        # itens=[], # Preencher com os itens formatados
        data_abertura=comanda_ativa.data_criacao
    )
    return comanda_digital_data

# Adicionar outros endpoints relacionados a comanda, como adicionar item (que na verdade é criar Pedido/ItemPedido)
# ou registrar pagamento (que será em endpoints de Pagamento).

