import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import fiado as crud_fiado, cliente as crud_cliente, comanda as crud_comanda
from app.db.database import get_db
from app.models import Usuario as DBUsuario, Fiado as DBFiado, StatusFiado
from app.services.auth_service import AuthService
from app.services.redis_service import RedisService
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=schemas.Fiado, status_code=status.HTTP_201_CREATED)
async def create_fiado(
    fiado_in: schemas.FiadoCreate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Fiado:
    """
    Registra um novo valor em fiado para um cliente.
    Pode estar associado a uma comanda ou ser um crédito direto.
    """
    try:
        # Verifica se o cliente existe
        cliente = crud_cliente.get(db, id=fiado_in.id_cliente)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        # Se associado a comanda, verifica se a comanda existe
        if fiado_in.id_comanda_origem:
            comanda = crud_comanda.get(db, id=fiado_in.id_comanda_origem)
            if not comanda:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comanda não encontrada"
                )

        # Cria o registro de fiado
        db_fiado = crud_fiado.create(
            db=db,
            obj_in=fiado_in,
            id_usuario_registrou=current_user.id
        )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"cliente_{fiado_in.id_cliente}_fiados",
            message={
                "event": "fiado_criado",
                "fiado_id": str(db_fiado.id),
                "cliente_id": str(fiado_in.id_cliente),
                "valor": float(db_fiado.valor_devido),
                "registrado_por": current_user.email
            }
        )

        logger.info(f"Fiado {db_fiado.id} criado por {current_user.email}")
        return db_fiado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar fiado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao registrar fiado"
        )

@router.get("/cliente/{cliente_id}", response_model=List[schemas.Fiado])
async def get_fiados_cliente(
    cliente_id: uuid.UUID,
    status: Optional[StatusFiado] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.Fiado]:
    """
    Lista os fiados de um cliente específico.
    Pode ser filtrado por status (Pendente, Pago Parcialmente, Pago Totalmente).
    """
    try:
        # Verifica se o cliente existe
        cliente = crud_cliente.get(db, id=cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        return crud_fiado.get_by_cliente(
            db=db,
            cliente_id=cliente_id,
            status=status,
            skip=skip,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar fiados do cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar fiados"
        )

@router.get("/{fiado_id}", response_model=schemas.FiadoDetail)
async def get_fiado(
    fiado_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.FiadoDetail:
    """
    Obtém detalhes de um registro de fiado específico.
    Inclui informações da comanda associada (se houver) e histórico de pagamentos.
    """
    try:
        fiado = crud_fiado.get(db, id=fiado_id)
        if not fiado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de fiado não encontrado"
            )

        # Verifica se o usuário tem permissão (admin ou gerente)
        if current_user.cargo not in ["admin", "gerente"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para acessar este registro"
            )

        return fiado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter fiado {fiado_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter registro de fiado"
        )

@router.post("/{fiado_id}/pagar", response_model=schemas.Fiado)
async def registrar_pagamento_fiado(
    fiado_id: uuid.UUID,
    pagamento: schemas.FiadoPagamentoCreate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Fiado:
    """
    Registra um pagamento para um fiado existente.
    Atualiza o valor devido e status do fiado.
    """
    try:
        if pagamento.valor <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valor do pagamento deve ser positivo"
            )

        # Registra o pagamento
        fiado, message = await crud_fiado.registrar_pagamento(
            db=db,
            fiado_id=fiado_id,
            valor_pago=pagamento.valor,
            metodo_pagamento=pagamento.metodo_pagamento,
            observacoes=pagamento.observacoes,
            id_usuario_registrou=current_user.id
        )

        if not fiado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"cliente_{fiado.id_cliente}_fiados",
            message={
                "event": "pagamento_fiado",
                "fiado_id": str(fiado.id),
                "valor_pago": float(pagamento.valor),
                "saldo_restante": float(fiado.valor_devido),
                "registrado_por": current_user.email
            }
        )

        logger.info(f"Pagamento de {pagamento.valor} registrado no fiado {fiado_id} por {current_user.email}")
        return fiado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar pagamento no fiado {fiado_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao registrar pagamento"
        )

@router.put("/{fiado_id}", response_model=schemas.Fiado)
async def update_fiado(
    fiado_id: uuid.UUID,
    fiado_in: schemas.FiadoUpdate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> schemas.Fiado:
    """
    Atualiza informações de um fiado (apenas administradores).
    Não deve ser usado para registrar pagamentos - use o endpoint /pagar.
    """
    try:
        db_fiado = crud_fiado.get(db, id=fiado_id)
        if not db_fiado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de fiado não encontrado"
            )

        # Valida se não está tentando atualizar valores de pagamento
        if fiado_in.valor_devido is not None or fiado_in.valor_pago is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para atualizar valores de fiado, use o endpoint de pagamento"
            )

        updated_fiado = crud_fiado.update(db, db_obj=db_fiado, obj_in=fiado_in)
        logger.info(f"Fiado {fiado_id} atualizado por {current_user.email}")
        return updated_fiado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar fiado {fiado_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar fiado"
        )