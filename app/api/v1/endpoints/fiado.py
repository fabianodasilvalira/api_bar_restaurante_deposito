# app/api/v1/endpoints/fiado.py
import uuid
from typing import List, Any, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.schemas.fiado_schemas import StatusFiado, FiadoSchemas, \
    FiadoUpdateSchemas, FiadoCreateSchemas  # Corrigido para importar StatusFiado e FiadoSchemas corretamente

from app.models.usuario import Usuario

router = APIRouter()


@router.post("/", response_model=FiadoSchemas, status_code=status.HTTP_201_CREATED)
def create_fiado_registro(
    *,
    db: Session = Depends(deps.get_db),
    fiado_in: FiadoCreateSchemas,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Registra um novo valor em fiado para um cliente e uma comanda.
    Este endpoint é chamado quando um pagamento é feito com o método "FiadoSchemas"
    ou quando se quer adicionar um valor diretamente ao fiado de uma comanda.
    """
    try:
        fiado_registro = crud.fiado.create(db=db, obj_in=fiado_in, id_usuario_registrou=current_user.id)
        # A lógica de publicação no Redis está comentada no CRUD por enquanto.
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return fiado_registro

@router.get("/cliente/{cliente_id}", response_model=List[FiadoSchemas])
def read_fiados_by_cliente(
    cliente_id: uuid.UUID,
    status_fiado: Optional[StatusFiado] = None,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera a lista de fiados de um cliente específico, opcionalmente filtrada por status.
    """
    cliente_db = crud.cliente.get(db, id=cliente_id)
    if not cliente_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    
    fiados = crud.fiado.get_multi_by_cliente(db, cliente_id=cliente_id, status=status_fiado, skip=skip, limit=limit)
    return fiados

@router.get("/{fiado_id}", response_model=FiadoSchemas)
def read_fiado_by_id(
    fiado_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera um registro de fiado pelo seu ID.
    """
    fiado_registro = crud.fiado.get(db=db, id=fiado_id)
    if not fiado_registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de fiado não encontrado")
    return fiado_registro

@router.put("/{fiado_id}/pagar", response_model=FiadoSchemas)
def registrar_pagamento_de_fiado(
    *,
    db: Session = Depends(deps.get_db),
    fiado_id: uuid.UUID,
    valor_pago: Decimal, # Poderia ser um schema FiadoSchemasPagamentoCreate com mais detalhes
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Registra um pagamento para um fiado existente.
    Atualiza o valor devido e o status do fiado, e os valores/status da comanda associada.
    """
    if valor_pago <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valor do pagamento deve ser positivo.")
    try:
        fiado_atualizado = crud.fiado.registrar_pagamento_fiado(
            db=db, 
            fiado_id=fiado_id, 
            valor_pago=valor_pago, 
            id_usuario_registrou=current_user.id
        )
        if not fiado_atualizado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de fiado não encontrado para pagamento.")
        # Notificar no Redis
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return fiado_atualizado

@router.put("/{fiado_id}", response_model=FiadoSchemas)
def update_fiado_registro(
    *,
    db: Session = Depends(deps.get_db),
    fiado_id: uuid.UUID,
    fiado_in: FiadoUpdateSchemas, # Usar FiadoSchemasUpdate que não permite pagamento direto por aqui
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Atualiza um registro de fiado (ex: observações, data de vencimento, status manual).
    Para registrar pagamento, use o endpoint /pagar.
    """
    fiado_db = crud.fiado.get(db=db, id=fiado_id)
    if not fiado_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de fiado não encontrado")
    
    if fiado_in.valor_pago_neste_momento is not None:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Para registrar pagamento em fiado, use o endpoint /{fiado_id}/pagar.")

    try:
        fiado_atualizado = crud.fiado.update(db=db, db_obj=fiado_db, obj_in=fiado_in)
    except ValueError as e: # Caso o CRUD de update lance algum erro de validação
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return fiado_atualizado

# Endpoints de relatório de fiado serão em relatorios.py

