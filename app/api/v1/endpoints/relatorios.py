# app/api/v1/endpoints/relatorios.py
from typing import Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.models.usuario import Usuario
from app.schemas.relatorio_schemas import RelatorioFiadoSchemas

router = APIRouter()

@router.get("/fiado", response_model=RelatorioFiadoSchemas)
def get_relatorio_fiado_endpoint(
    data_inicio: date, # Query parameter
    data_fim: date,    # Query parameter
    db: Session = Depends(deps.get_db),
    current_user: Usuario = Depends(deps.get_current_active_superuser) # Apenas superusuários podem ver relatórios
) -> Any:
    """
    Gera um relatório de fiados pendentes e parcialmente pagos.
    O relatório considera fiados que estavam com status Pendente ou Pago Parcialmente
    no final do período `data_fim` e que foram criados em qualquer momento até `data_fim`.
    """
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data de início não pode ser posterior à data de fim."
        )
    
    # A lógica de geração do relatório está em crud.fiado.get_relatorio_fiado
    try:
        relatorio = crud.fiado.get_relatorio_fiado(db=db, data_inicio=data_inicio, data_fim=data_fim)
    except Exception as e:
        # Logar o erro e retornar um erro genérico
        # logger.error(f"Erro ao gerar relatório de fiado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao gerar o relatório de fiado: {e}"
        )
    
    return relatorio

# Outros endpoints de relatório podem ser adicionados aqui (ex: vendas, produtos mais vendidos, etc.)

