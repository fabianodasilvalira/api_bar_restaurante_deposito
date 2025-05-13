# app/api/v1/endpoints/mesas.py
import uuid
from typing import List, Any, Optional
import qrcode # Para gerar a imagem do QR Code
import io # Para enviar a imagem do QR Code

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação

from app.models.usuario import Usuario
from app.schemas.mesa_schemas import MesaComComandaInfo

# from app.services.redis_service import redis_client # Para publicar eventos no Redis
# import json # Para formatar mensagens Redis

router = APIRouter()

@router.post("/", response_model=MesaComComandaInfo, status_code=status.HTTP_201_CREATED)
def create_mesa(
    *, 
    db: Session = Depends(deps.get_db),
    mesa_in: schemas.MesaCreate,
    current_user: Usuario = Depends(deps.get_current_active_superuser) # Apenas superusuários podem criar mesas
) -> Any:
    """
    Cria uma nova mesa.
    Gera automaticamente um QR Code hash para ela.
    """
    try:
        mesa = crud.mesa.create(db=db, obj_in=mesa_in)
        # Ao criar uma mesa, ela geralmente está disponível, não se abre uma comanda automaticamente aqui.
        # A comanda é aberta através de um endpoint específico de "abrir mesa".
        # Portanto, id_comanda_ativa será None inicialmente.
        return MesaComComandaInfo(**mesa.__dict__, id_comanda_ativa=None)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# @router.get("/", response_model=List[schemas.Mesa])
# def read_mesas(
#     db: Session = Depends(deps.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     status_mesa: Optional[StatusMesa] = None,
#     current_user: Usuario = Depends(deps.get_current_active_user)
# ) -> Any:
#     """
#     Recupera a lista de mesas, opcionalmente filtrada por status.
#     """
#     mesas = crud.mesa.get_multi(db, skip=skip, limit=limit, status=status_mesa)
#     return mesas

@router.get("/{mesa_id}", response_model=schemas.Mesa)
def read_mesa_by_id(
    mesa_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera uma mesa pelo seu ID.
    """
    mesa = crud.mesa.get(db=db, id=mesa_id)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada")
    return mesa

@router.put("/{mesa_id}", response_model=schemas.Mesa)
def update_mesa(
    *,
    db: Session = Depends(deps.get_db),
    mesa_id: uuid.UUID,
    mesa_in: schemas.MesaUpdate,
    current_user: Usuario = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Atualiza uma mesa.
    """
    mesa = crud.mesa.get(db=db, id=mesa_id)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada")
    try:
        mesa = crud.mesa.update(db=db, db_obj=mesa, obj_in=mesa_in)
        # Publicar no Redis se o status da mesa mudar, por exemplo
        # if mesa_in.status:
        #     await redis_client.publish_message(f"mesa_{mesa.id}_status", json.dumps({"status": mesa.status.value}))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return mesa

@router.delete("/{mesa_id}", response_model=schemas.Mesa)
def delete_mesa(
    *,
    db: Session = Depends(deps.get_db),
    mesa_id: uuid.UUID,
    current_user: Usuario = Depends(deps.get_current_active_superuser)
) -> Any:
    """
    Deleta uma mesa.
    """
    mesa = crud.mesa.get(db=db, id=mesa_id)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada")
    try:
        mesa_removida = crud.mesa.remove(db=db, id=mesa_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return mesa_removida

@router.post("/{mesa_id}/abrir", response_model=MesaComComandaInfo)
def abrir_mesa_endpoint(
    mesa_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    id_cliente_associado: Optional[uuid.UUID] = None, # Pode ser passado no corpo da requisição também
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Abre uma mesa, mudando seu status para OCUPADA e criando uma nova comanda.
    """
    # A lógica de criar a comanda real será integrada quando crud_comanda estiver pronto.
    # Por enquanto, crud.mesa.abrir_mesa retorna um placeholder para id_comanda_ativa.
    mesa, id_comanda_ativa, error_message = crud.mesa.abrir_mesa(db=db, mesa_id=mesa_id, id_cliente_associado=id_cliente_associado)
    if error_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada ao tentar abrir.")

    # Publicar evento no Redis sobre a abertura da mesa (a lógica de publish está comentada no CRUD por enquanto)
    # await redis_client.publish_message(f"mesa_{mesa.id}_status", json.dumps({"status": "OCUPADA", "comanda_id": str(id_comanda_ativa)}))

    return MesaComComandaInfo(**mesa.__dict__, id_comanda_ativa=id_comanda_ativa)

@router.post("/{mesa_id}/fechar", response_model=schemas.Mesa)
def fechar_mesa_endpoint(
    mesa_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Fecha uma mesa (geralmente após o pagamento da comanda).
    """
    mesa, error_message = crud.mesa.fechar_mesa(db=db, mesa_id=mesa_id)
    if error_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada ao tentar fechar.")

    # Publicar evento no Redis (a lógica de publish está comentada no CRUD por enquanto)
    # await redis_client.publish_message(f"mesa_{mesa.id}_status", json.dumps({"status": "FECHADA"}))
    return mesa

@router.get("/{mesa_id}/qrcode", responses={200: {"content": {"image/png": {}}}}, response_class=Response)
def get_mesa_qrcode(
    mesa_id: uuid.UUID,
    db: Session = Depends(deps.get_db)
    # current_user: Usuario = Depends(deps.get_current_active_user) # Acesso ao QR Code pode ser público ou restrito
) -> Response:
    """
    Gera e retorna a imagem do QR Code para uma mesa.
    O QR Code conterá o qr_code_hash da mesa, que será usado para acessar a comanda digital.
    """
    mesa = crud.mesa.get(db=db, id=mesa_id)
    if not mesa or not mesa.qr_code_hash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa ou QR Code hash não encontrado.")

    # Idealmente, a URL base para a comanda digital viria da configuração
    # Ex: f"{settings.COMANDA_DIGITAL_BASE_URL}/{mesa.qr_code_hash}"
    # Por agora, vamos apenas usar o hash como dado do QR Code.
    qr_data = mesa.qr_code_hash 
    # Ou uma URL completa: qr_data = f"http://localhost:3000/comanda/{mesa.qr_code_hash}" (exemplo)
    
    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@router.get("/qrcode/{qr_code_hash}", response_model=schemas.Mesa) # Endpoint para testar o hash
def get_mesa_by_qrcode_hash(
    qr_code_hash: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    (Para teste) Recupera uma mesa pelo seu qr_code_hash.
    A comanda digital usaria este hash para buscar os dados da comanda associada.
    """
    mesa = crud.mesa.get_by_qr_code_hash(db, qr_code_hash=qr_code_hash)
    if not mesa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mesa encontrada para este QR Code hash.")
    return mesa

