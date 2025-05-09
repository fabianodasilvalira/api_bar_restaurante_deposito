import uuid
from asyncio.log import logger
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.auth import AuthService
from app.crud import crud_comanda as crud_comanda, crud_mesa as crud_mesa
from app.database import get_db
from app.db.models.comanda import StatusComanda
from app.models import Usuario as DBUsuario, Comanda as DBComanda
from app.services.pedido_service import PedidoService
from app.services.redis_service import RedisService

router = APIRouter()


@router.get("/", response_model=List[schemas.Comanda])
async def list_comandas(
        skip: int = 0,
        limit: int = 100,
        status_comanda: Optional[StatusComanda] = None,
        mesa_id: Optional[uuid.UUID] = None,
        cliente_id: Optional[uuid.UUID] = None,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.Comanda]:
    """
    Lista comandas com filtros opcionais:
    - status_comanda: Filtra por status específico
    - mesa_id: Filtra por mesa específica
    - cliente_id: Filtra por cliente específico
    """
    try:
        if mesa_id:
            return crud_comanda.get_by_mesa(db, mesa_id=mesa_id, skip=skip, limit=limit)
        elif cliente_id:
            return crud_comanda.get_by_cliente(db, cliente_id=cliente_id, skip=skip, limit=limit)
        else:
            return crud_comanda.get_multi(db, skip=skip, limit=limit, status=status_comanda)
    except Exception as e:
        logger.error(f"Erro ao listar comandas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar comandas"
        )


@router.get("/{comanda_id}", response_model=schemas.ComandaDetail)
async def get_comanda(
        comanda_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.ComandaDetail:
    """
    Obtém detalhes de uma comanda específica, incluindo:
    - Informações básicas da comanda
    - Lista de pedidos
    - Itens de cada pedido
    - Pagamentos realizados
    """
    try:
        comanda = crud_comanda.get(db, id=comanda_id)
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Verifica se o usuário tem permissão para acessar esta comanda
        if current_user.cargo not in ["admin", "gerente"]:
            if comanda.mesa and comanda.mesa.id_usuario_responsavel != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar esta comanda"
                )

        # Usa o serviço para calcular o valor total atualizado
        await PedidoService().calculate_comanda_total(db, comanda_id=comanda_id)

        return comanda
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter comanda {comanda_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter comanda"
        )


@router.put("/{comanda_id}", response_model=schemas.Comanda)
async def update_comanda(
        comanda_id: uuid.UUID,
        comanda_in: schemas.ComandaUpdate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Comanda:
    """
    Atualiza informações de uma comanda:
    - Observações
    - Status (com validações de transição)
    """
    try:
        db_comanda = crud_comanda.get(db, id=comanda_id)
        if not db_comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada"
            )

        # Valida transição de status se necessário
        if comanda_in.status_comanda:
            if db_comanda.status_comanda in ["FECHADA", "CANCELADA"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não é possível alterar comanda com status {db_comanda.status_comanda}"
                )

        updated_comanda = crud_comanda.update(db, db_obj=db_comanda, obj_in=comanda_in)

        # Publica evento de atualização
        await RedisService().publish(
            channel=f"comanda_{comanda_id}_updates",
            message={
                "event": "comanda_updated",
                "comanda_id": str(comanda_id),
                "status": updated_comanda.status_comanda.value,
                "updated_by": current_user.email
            }
        )

        logger.info(f"Comanda {comanda_id} atualizada por {current_user.email}")
        return updated_comanda

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar comanda {comanda_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar comanda"
        )


@router.post("/{comanda_id}/fechar", response_model=schemas.Comanda)
async def fechar_comanda(
        comanda_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Comanda:
    """
    Fecha uma comanda para pagamento:
    - Recalcula totais
    - Atualiza status
    - Libera a mesa se aplicável
    """
    try:
        # Usa o serviço para fechar a comanda
        comanda, message = await PedidoService().fechar_comanda(
            db=db,
            comanda_id=comanda_id,
            current_user=current_user
        )

        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Publica evento de fechamento
        await RedisService().publish(
            channel=f"comanda_{comanda_id}_events",
            message={
                "event": "comanda_fechada",
                "comanda_id": str(comanda_id),
                "valor_total": float(comanda.valor_total),
                "valor_pago": float(comanda.valor_pago),
                "valor_restante": float(comanda.valor_total - comanda.valor_pago)
            }
        )

        logger.info(f"Comanda {comanda_id} fechada por {current_user.email}")
        return comanda

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fechar comanda {comanda_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao fechar comanda"
        )


@router.get("/digital/{qr_code_hash}", response_model=schemas.ComandaDigital)
async def get_comanda_digital(
    qr_code_hash: str,
    db: Session = Depends(get_db)
) -> schemas.ComandaDigital:
    """
    Endpoint público para visualização da comanda via QR Code
    Retorna informações limitadas para o cliente
    """
    try:
        mesa = crud_mesa.get_by_qr_hash(db, qr_code_hash=qr_code_hash)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR Code inválido ou mesa não encontrada"
            )

        comanda = crud_comanda.get_ativa_by_mesa(db, mesa_id=mesa.id)
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma comanda ativa para esta mesa"
            )

        # Calcula valores
        valor_restante = comanda.valor_total - comanda.valor_pago
        if valor_restante < 0:
            valor_restante = Decimal("0.00")

        itens = await _get_itens_comanda(db, comanda)

        return schemas.ComandaDigital(
            id=comanda.id,
            mesa_numero=mesa.numero_identificador,
            status=comanda.status_comanda.value,
            valor_total=comanda.valor_total,
            valor_pago=comanda.valor_pago,
            valor_restante=valor_restante,
            data_abertura=comanda.data_criacao,
            itens=itens  # Adicione esse campo ao seu schema se ainda não estiver lá
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao acessar comanda digital: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao acessar comanda"
        )

async def _get_itens_comanda(db: Session, db_comanda: DBComanda) -> List[
    schemas.ItemPedidoComandaDigital]:  # Assinatura alterada
    """Obtém itens da comanda formatados para visualização do cliente."""
    itens_formatados = []

    # Verifica se a comanda e seus itens existem para evitar erros
    if not db_comanda or not hasattr(db_comanda, 'itens_pedido') or not db_comanda.itens_pedido:
        logger.info(
            f"Comanda {db_comanda.id if db_comanda and hasattr(db_comanda, 'id') else 'desconhecida'} não possui itens ou itens não carregados.")
        return itens_formatados

    for item_pedido in db_comanda.itens_pedido:
        nome_produto_str = "Produto não informado"
        # Verifica se o relacionamento 'produto' e o atributo 'nome' existem
        if hasattr(item_pedido, 'produto') and item_pedido.produto and hasattr(item_pedido.produto, 'nome'):
            nome_produto_str = item_pedido.produto.nome
        else:
            logger.warning(
                f"Item de pedido {item_pedido.id if hasattr(item_pedido, 'id') else 'desconhecido'} sem produto associado ou nome do produto na comanda {db_comanda.id if db_comanda and hasattr(db_comanda, 'id') else 'desconhecida'}.")

        status_str = "Status Indefinido"
        # Verifica se o atributo 'status_item_pedido' e 'value' existem
        if hasattr(item_pedido, 'status_item_pedido') and item_pedido.status_item_pedido and hasattr(
                item_pedido.status_item_pedido, 'value'):
            status_str = item_pedido.status_item_pedido.value
        else:
            logger.warning(
                f"Item de pedido {item_pedido.id if hasattr(item_pedido, 'id') else 'desconhecido'} sem status ou valor de status na comanda {db_comanda.id if db_comanda and hasattr(db_comanda, 'id') else 'desconhecida'}.")

        # Garante que os atributos básicos do item_pedido existem
        quantidade = item_pedido.quantidade if hasattr(item_pedido, 'quantidade') else 0
        preco_total_item = item_pedido.preco_total_item if hasattr(item_pedido, 'preco_total_item') else Decimal("0.0")
        observacoes = item_pedido.observacoes_item if hasattr(item_pedido, 'observacoes_item') else None

        itens_formatados.append(
            schemas.ItemPedidoComandaDigital(
                nome_produto=nome_produto_str,
                quantidade=quantidade,
                preco_total_item=preco_total_item,
                status_item_pedido=status_str,
                observacoes=observacoes
            )
        )

    return itens_formatados