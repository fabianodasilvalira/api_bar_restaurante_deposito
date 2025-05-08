import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.crud import pagamento as crud_pagamento, comanda as crud_comanda
from app.db.database import get_db
from app.models import Usuario as DBUsuario, Pagamento as DBPagamento, MetodoPagamento
from app.services.auth_service import AuthService
from app.services.redis_service import RedisService
from app.services.pagamento_service import PagamentoService
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=schemas.Pagamento, status_code=status.HTTP_201_CREATED)
async def registrar_pagamento(
    pagamento_in: schemas.PagamentoCreate,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Pagamento:
    """
    Registra um novo pagamento para uma comanda.
    Atualiza automaticamente o status e valores da comanda.
    Se o método for FIADO, cria um registro de fiado associado.
    """
    try:
        # Validação básica
        if pagamento_in.valor <= Decimal('0'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valor do pagamento deve ser positivo"
            )

        # Verifica se a comanda existe
        comanda = crud_comanda.get(db, id=pagamento_in.id_comanda)
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Usa o serviço para registrar o pagamento
        pagamento, message = await PagamentoService().registrar_pagamento(
            db=db,
            pagamento_in=pagamento_in,
            usuario_id=current_user.id
        )

        if not pagamento:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"comanda_{pagamento_in.id_comanda}_pagamentos",
            message={
                "event": "pagamento_registrado",
                "pagamento_id": str(pagamento.id),
                "valor": float(pagamento.valor),
                "metodo": pagamento.metodo_pagamento.value,
                "registrado_por": current_user.email
            }
        )

        logger.info(f"Pagamento {pagamento.id} registrado por {current_user.email}")
        return pagamento

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar pagamento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao registrar pagamento"
        )

@router.get("/comanda/{comanda_id}", response_model=List[schemas.Pagamento])
async def listar_pagamentos_comanda(
    comanda_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    metodo: Optional[MetodoPagamento] = None,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.Pagamento]:
    """
    Lista todos os pagamentos de uma comanda específica.
    Pode ser filtrado por método de pagamento.
    """
    try:
        # Verifica se a comanda existe
        comanda = crud_comanda.get(db, id=comanda_id)
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Verifica permissão (admin/gerente ou usuário responsável pela mesa)
        if current_user.cargo not in ["admin", "gerente"]:
            if comanda.mesa and comanda.mesa.id_usuario_responsavel != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar estes pagamentos"
                )

        return crud_pagamento.get_by_comanda(
            db=db,
            comanda_id=comanda_id,
            skip=skip,
            limit=limit,
            metodo=metodo
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar pagamentos da comanda {comanda_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar pagamentos"
        )

@router.get("/{pagamento_id}", response_model=schemas.PagamentoDetail)
async def obter_pagamento(
    pagamento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.PagamentoDetail:
    """
    Obtém detalhes de um pagamento específico.
    Inclui informações da comanda associada e usuário que registrou.
    """
    try:
        pagamento = crud_pagamento.get(db, id=pagamento_id)
        if not pagamento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pagamento não encontrado"
            )

        # Verifica permissão
        if current_user.cargo not in ["admin", "gerente"]:
            if pagamento.comanda.mesa and pagamento.comanda.mesa.id_usuario_responsavel != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar este pagamento"
                )

        return pagamento

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter pagamento {pagamento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter pagamento"
        )

@router.post("/{pagamento_id}/estornar", response_model=schemas.Pagamento)
async def estornar_pagamento(
    pagamento_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> schemas.Pagamento:
    """
    Estorna um pagamento registrado (apenas administradores).
    Cria um pagamento negativo para compensar e atualiza a comanda.
    """
    try:
        # Usa o serviço para estornar o pagamento
        pagamento_estornado, message = await PagamentoService().estornar_pagamento(
            db=db,
            pagamento_id=pagamento_id,
            usuario_id=current_user.id
        )

        if not pagamento_estornado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento no Redis
        await RedisService().publish(
            channel=f"comanda_{pagamento_estornado.id_comanda}_pagamentos",
            message={
                "event": "pagamento_estornado",
                "pagamento_id": str(pagamento_estornado.id),
                "valor": float(pagamento_estornado.valor),
                "estornado_por": current_user.email
            }
        )

        logger.info(f"Pagamento {pagamento_id} estornado por {current_user.email}")
        return pagamento_estornado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao estornar pagamento {pagamento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao estornar pagamento"
        )