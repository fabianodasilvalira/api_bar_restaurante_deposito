# app/schemas/relatorio.py
import uuid
from typing import List, Optional
from decimal import Decimal
from datetime import date

from pydantic import BaseModel

# Este schema já foi definido na primeira entrega e no crud_fiado.py
# Mantendo aqui para consistência da estrutura de pastas.

class RelatorioFiadoItemSchemas(BaseModel):
    id_cliente: uuid.UUID
    nome_cliente: Optional[str] = "Cliente não informado"
    valor_total_devido: Decimal
    quantidade_fiados_pendentes: int
    # data_ultimo_fiado: Optional[datetime] = None # Poderia ser útil

    class Config:
        from_attributes = True

class RelatorioFiadoSchemas(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_geral_devido: Decimal
    total_fiados_registrados_periodo: int  # Número de transações de fiado em aberto no período
    detalhes_por_cliente: List[RelatorioFiadoItemSchemas]  # Corrigido o nome para RelatorioFiadoItemSchemas

    class Config:
        from_attributes = True
