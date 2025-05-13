# app/api/v1/endpoints/pagamentos.py
import uuid
from typing import List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.models.usuario import Usuario

router = APIRouter()

@router.post("/", response_model=schemas.Pagamento, status_code=status.HTTP_201_CREATED)
def create_pagamento(
    *, 
    db: Session = Depends(deps.get_db),
    pagamento_in: schemas.PagamentoCreate,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Registra um novo pagamento para uma comanda.
    Atualiza os valores e status da comanda.
    Se o método for FIADO, registra o valor no fiado da comanda.
    """
    try:
        pagamento = crud.pagamento.create(db=db, obj_in=pagamento_in, id_usuario_registrou=current_user.id)
        # A lógica de publicação no Redis está comentada no CRUD por enquanto.
        # Se movida para cá, seria chamada aqui.
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return pagamento

@router.get("/comanda/{comanda_id}", response_model=List[schemas.Pagamento])
def read_pagamentos_by_comanda(
    comanda_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera a lista de pagamentos de uma comanda específica.
    """
    # Verificar se a comanda existe primeiro
    comanda_db = crud.comanda.get(db, id=comanda_id)
    if not comanda_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda não encontrada")
    
    pagamentos = crud.pagamento.get_multi_by_comanda(db, comanda_id=comanda_id, skip=skip, limit=limit)
    return pagamentos

@router.get("/{pagamento_id}", response_model=schemas.Pagamento)
def read_pagamento_by_id(
    pagamento_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_user)
) -> Any:
    """
    Recupera um pagamento pelo seu ID.
    """
    pagamento = crud.pagamento.get(db=db, id=pagamento_id)
    if not pagamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
    return pagamento

# Geralmente pagamentos não são deletados, mas podem ser cancelados (novo status ou estorno).
# Se for necessário um endpoint para cancelar/estornar, ele seria implementado aqui.

