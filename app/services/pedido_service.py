# app/services/pedido_service.py
import uuid
import json
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.crud import crud_pedido # Assuming crud_pedido will be in app.crud
from app.db.models.usuario import Usuario as DBUsuario # Model for current_user type hint
from app.db.models.pedido import Pedido as DBPedido # Model for return type hint
from app.services.redis_service import redis_client

async def update_pedido_status_and_notify(
    db: Session,
    *, 
    pedido_id: uuid.UUID, 
    status_novo: str, 
    current_user: DBUsuario
) -> Tuple[Optional[DBPedido], Optional[str]]:
    """
    Updates the status of a pedido and publishes a notification to Redis.
    Returns the updated pedido object and an optional error message.
    """
    # Note: crud_pedido.update_status is assumed to be a synchronous function.
    # In a high-concurrency async application, blocking DB calls should ideally be
    # handled with something like `run_in_threadpool` or by using an async ORM setup.
    # For this step, we call it directly from an async function.
    
    # First, update the status in the database using the CRUD operation
    # This function needs to be created/refactored in crud_pedido.py
    # It should handle the database transaction and return the updated pedido and a message/error.
    # For now, let's assume a simplified signature for crud_pedido.update_status
    # db_pedido, message = crud_pedido.pedido.update_status(db=db, pedido_id=pedido_id, status_novo=status_novo, current_user=current_user)
    
    # Placeholder for the actual CRUD call - this needs to be implemented based on the refactored crud_pedido.py
    # For now, let's simulate a successful update for the Redis part.
    # In a real scenario, you'd fetch the pedido, update its status, and commit.
    # The original crud.py had a more complex update_pedido_status, let's assume it's refactored into crud_pedido.py

    # This is a simplified version of what should be in crud_pedido.py's update_status method
    # This logic will be moved to the actual crud_pedido.py later in the refactoring step.
    db_pedido = db.query(DBPedido).filter(DBPedido.id == pedido_id).first()
    message = None
    if not db_pedido:
        return None, "Pedido não encontrado"

    # Simplified status transition validation (actual validation should be in CRUD or service)
    allowed_transitions = {
        "Em preparo": ["Entregue", "Saiu para entrega", "Cancelado"],
        "Saiu para entrega": ["Entregue", "Cancelado"],
    }
    if db_pedido.status in ["Entregue", "Cancelado"]:
        return db_pedido, f"Pedido já está {db_pedido.status} e não pode ser alterado."
    if status_novo not in allowed_transitions.get(db_pedido.status, []):
        return db_pedido, f"Não é possível mudar status de 	\"{db_pedido.status}	\" para 	\"{status_novo}	\"."

    db_pedido.status = status_novo
    # db_pedido.data_ultima_atualizacao_status = func.now() # This would require func from sqlalchemy
    try:
        db.commit()
        db.refresh(db_pedido)
        message = f"Status do pedido atualizado para {status_novo}"

        # If the DB update was successful, publish to Redis
        if db_pedido:
            redis_message = {
                "pedido_id": str(db_pedido.id),
                "novo_status": db_pedido.status,
                "mesa_id": str(db_pedido.comanda.id_mesa) if db_pedido.comanda else None,
                "timestamp": datetime.utcnow().isoformat() # Requires datetime import
            }
            # Channel could be more specific, e.g., f"mesa_{db_pedido.comanda.id_mesa}_pedidos"
            await redis_client.publish_message(channel="pedidos_status_updates", message=json.dumps(redis_message))
            # For specific client notifications, a channel like f"cliente_{client_id}_notificacoes" or f"mesa_{mesa_id}_notificacoes" might be used.
            # For restaurant dashboard, a general channel like "cozinha_pedidos" or "restaurante_dashboard_updates".

    except Exception as e:
        db.rollback()
        return None, f"Erro ao atualizar pedido no banco: {str(e)}"
        
    return db_pedido, message

# Need to import datetime for the timestamp
from datetime import datetime

