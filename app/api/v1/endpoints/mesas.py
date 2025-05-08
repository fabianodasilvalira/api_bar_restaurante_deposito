import uuid
import qrcode
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app import schemas
from app.crud import mesa as crud_mesa, comanda as crud_comanda
from app.db.database import get_db
from app.models import Usuario as DBUsuario, Mesa as DBMesa, StatusMesa
from app.services.auth_service import AuthService
from app.services.redis_service import RedisService
from app.services.mesa_service import MesaService
from app.core.logging import logger
from app.core.config import settings

router = APIRouter()


@router.post("/", response_model=schemas.Mesa, status_code=status.HTTP_201_CREATED)
async def create_mesa(
        mesa_in: schemas.MesaCreate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> schemas.Mesa:
    """
    Cria uma nova mesa (apenas administradores).
    Gera automaticamente um QR Code único.
    """
    try:
        # Verifica se já existe mesa com o mesmo número
        existing_mesa = crud_mesa.get_by_numero(db, numero=mesa_in.numero_identificador)
        if existing_mesa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe uma mesa com o número {mesa_in.numero_identificador}"
            )

        # Usa o serviço para criar a mesa
        mesa = await MesaService().create_mesa(db=db, mesa_in=mesa_in)

        logger.info(f"Mesa {mesa.id} criada por {current_user.email}")
        return mesa

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar mesa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar mesa"
        )


@router.get("/", response_model=List[schemas.Mesa])
async def list_mesas(
        skip: int = 0,
        limit: int = 100,
        status: Optional[StatusMesa] = None,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> List[schemas.Mesa]:
    """
    Lista todas as mesas com filtro opcional por status.
    """
    try:
        return crud_mesa.get_multi(db, skip=skip, limit=limit, status=status)
    except Exception as e:
        logger.error(f"Erro ao listar mesas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar mesas"
        )


@router.get("/{mesa_id}", response_model=schemas.MesaDetail)
async def get_mesa(
        mesa_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.MesaDetail:
    """
    Obtém detalhes de uma mesa específica, incluindo:
    - Informações da mesa
    - Comanda ativa (se houver)
    - Cliente associado (se houver)
    """
    try:
        mesa = crud_mesa.get(db, id=mesa_id)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa não encontrada"
            )

        # Obtém comanda ativa se existir
        comanda_ativa = None
        if mesa.status == StatusMesa.OCUPADA:
            comanda_ativa = crud_comanda.get_ativa_by_mesa(db, mesa_id=mesa.id)

        return schemas.MesaDetail(
            **mesa.__dict__,
            comanda_ativa=comanda_ativa,
            cliente=mesa.cliente_associado
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter mesa"
        )


@router.put("/{mesa_id}", response_model=schemas.Mesa)
async def update_mesa(
        mesa_id: uuid.UUID,
        mesa_in: schemas.MesaUpdate,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> schemas.Mesa:
    """
    Atualiza informações de uma mesa (apenas administradores).
    """
    try:
        db_mesa = crud_mesa.get(db, id=mesa_id)
        if not db_mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa não encontrada"
            )

        updated_mesa = crud_mesa.update(db, db_obj=db_mesa, obj_in=mesa_in)
        logger.info(f"Mesa {mesa_id} atualizada por {current_user.email}")
        return updated_mesa

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar mesa"
        )


@router.delete("/{mesa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesa(
        mesa_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_admin)
) -> None:
    """
    Remove uma mesa (apenas administradores).
    Só permite remoção se a mesa estiver livre.
    """
    try:
        mesa = crud_mesa.get(db, id=mesa_id)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa não encontrada"
            )

        if mesa.status != StatusMesa.LIVRE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível remover mesas livres"
            )

        crud_mesa.remove(db, id=mesa_id)
        logger.info(f"Mesa {mesa_id} removida por {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao remover mesa"
        )


@router.post("/{mesa_id}/abrir", response_model=schemas.MesaDetail)
async def abrir_mesa(
        mesa_id: uuid.UUID,
        cliente_id: Optional[uuid.UUID] = None,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.MesaDetail:
    """
    Abre uma mesa, mudando seu status para OCUPADA e criando uma nova comanda.
    """
    try:
        # Usa o serviço para abrir a mesa
        mesa, comanda = await MesaService().abrir_mesa(
            db=db,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            usuario_id=current_user.id
        )

        # Publica evento no Redis
        await RedisService().publish(
            channel="mesas_status",
            message={
                "event": "mesa_aberta",
                "mesa_id": str(mesa_id),
                "comanda_id": str(comanda.id) if comanda else None,
                "responsavel": current_user.email
            }
        )

        logger.info(f"Mesa {mesa_id} aberta por {current_user.email}")
        return schemas.MesaDetail(
            **mesa.__dict__,
            comanda_ativa=comanda,
            cliente=mesa.cliente_associado
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao abrir mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao abrir mesa"
        )


@router.post("/{mesa_id}/fechar", response_model=schemas.Mesa)
async def fechar_mesa(
        mesa_id: uuid.UUID,
        db: Session = Depends(get_db),
        current_user: DBUsuario = Depends(AuthService.get_current_active_user)
) -> schemas.Mesa:
    """
    Fecha uma mesa, mudando seu status para LIVRE.
    Verifica se a comanda associada está paga antes de fechar.
    """
    try:
        # Usa o serviço para fechar a mesa
        mesa = await MesaService().fechar_mesa(
            db=db,
            mesa_id=mesa_id,
            usuario_id=current_user.id
        )

        # Publica evento no Redis
        await RedisService().publish(
            channel="mesas_status",
            message={
                "event": "mesa_fechada",
                "mesa_id": str(mesa_id),
                "responsavel": current_user.email
            }
        )

        logger.info(f"Mesa {mesa_id} fechada por {current_user.email}")
        return mesa

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fechar mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao fechar mesa"
        )


@router.get("/{mesa_id}/qrcode", responses={200: {"content": {"image/png": {}}}}, response_class=Response)
async def get_qrcode(
        mesa_id: uuid.UUID,
        db: Session = Depends(get_db)
) -> Response:
    """
    Gera o QR Code para acesso à comanda digital da mesa.
    """
    try:
        mesa = crud_mesa.get(db, id=mesa_id)
        if not mesa or not mesa.qr_code_hash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa não encontrada ou sem QR Code"
            )

        # Gera a URL completa para a comanda digital
        qr_data = f"{settings.FRONTEND_URL}/comanda/{mesa.qr_code_hash}"

        # Gera a imagem do QR Code
        img = qrcode.make(qr_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Response(content=buf.getvalue(), media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar QR Code para mesa {mesa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao gerar QR Code"
        )


@router.get("/qrcode/{qr_code_hash}", response_model=schemas.Mesa)
async def get_mesa_by_qrcode(
        qr_code_hash: str,
        db: Session = Depends(get_db)
) -> schemas.Mesa:
    """
    Obtém os dados da mesa associada a um QR Code.
    Usado pelo frontend para validar QR Codes.
    """
    try:
        mesa = crud_mesa.get_by_qr_hash(db, qr_code_hash=qr_code_hash)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR Code inválido ou mesa não encontrada"
            )
        return mesa
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar mesa por QR Code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao validar QR Code"
        )