# app/crud/crud_mesa.py
import uuid
from typing import List, Optional, Union, Dict, Any, Tuple
import hashlib # Para gerar o qr_code_hash

from sqlalchemy.orm import Session
from sqlalchemy import func # Para func.now()

from app.db.models.mesa import Mesa, StatusMesa
from app.schemas.mesa import MesaCreateSchemas, MesaUpdateSchemas
# from app.crud import crud_comanda # Será necessário para abrir comanda ao abrir mesa

class CRUDMesa:
    def get(self, db: Session, id: uuid.UUID) -> Optional[Mesa]:
        return db.query(Mesa).filter(Mesa.id == id).first()

    def get_by_numero_identificador(self, db: Session, *, numero_identificador: str) -> Optional[Mesa]:
        return db.query(Mesa).filter(Mesa.numero_identificador == numero_identificador).first()
    
    def get_by_qr_code_hash(self, db: Session, *, qr_code_hash: str) -> Optional[Mesa]:
        return db.query(Mesa).filter(Mesa.qr_code_hash == qr_code_hash).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: Optional[StatusMesa] = None
    ) -> List[Mesa]:
        query = db.query(Mesa)
        if status:
            query = query.filter(Mesa.status == status)
        return query.order_by(Mesa.numero_identificador).offset(skip).limit(limit).all()

    def _generate_qr_code_hash(self, mesa_id: uuid.UUID, numero_identificador: str) -> str:
        # Cria um hash único para o QR Code baseado no ID da mesa e um timestamp/salt
        # Usar o ID da mesa garante unicidade. Adicionar um salt ou timestamp pode ser bom.
        # Para simplicidade, vamos usar o ID da mesa e o número identificador.
        timestamp = func.now() # Isso não é um valor fixo, mas para a semente do hash é ok.
        data_to_hash = f"{str(mesa_id)}-{numero_identificador}-{str(timestamp)}"
        return hashlib.sha256(data_to_hash.encode()).hexdigest()[:16] # Pega os primeiros 16 chars do hash

    def create(self, db: Session, *, obj_in: MesaCreateSchemas) -> Mesa:
        # Verificar se já existe mesa com o mesmo número identificador
        existing_mesa = self.get_by_numero_identificador(db, numero_identificador=obj_in.numero_identificador)
        if existing_mesa:
            raise ValueError(f"Mesa com o número identificador 	\"{obj_in.numero_identificador}	\" já existe.")

        db_obj = Mesa(
            numero_identificador=obj_in.numero_identificador,
            capacidade=obj_in.capacidade,
            status=obj_in.status if obj_in.status else StatusMesa.DISPONIVEL,
            id_cliente_associado=obj_in.id_cliente_associado
        )
        db.add(db_obj)
        db.commit() # Commit para obter o ID da mesa
        db.refresh(db_obj)

        # Gerar e atribuir o qr_code_hash após a mesa ter um ID
        if not db_obj.qr_code_hash:
            db_obj.qr_code_hash = self._generate_qr_code_hash(db_obj.id, db_obj.numero_identificador)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
        return db_obj

    def update(
        self, db: Session, *, db_obj: Mesa, obj_in: Union[MesaUpdateSchemas, Dict[str, Any]]
    ) -> Mesa:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if "numero_identificador" in update_data and update_data["numero_identificador"] != db_obj.numero_identificador:
            existing_mesa = self.get_by_numero_identificador(db, numero_identificador=update_data["numero_identificador"])
            if existing_mesa and existing_mesa.id != db_obj.id:
                raise ValueError(f"Outra mesa com o número identificador 	\"{update_data['numero_identificador']}	\" já existe.")

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: uuid.UUID) -> Optional[Mesa]:
        obj = db.query(Mesa).get(id)
        if obj:
            # Adicionar lógica para verificar se a mesa tem comandas abertas ou fiados pendentes
            # if any(comanda.status_comanda not in [StatusComanda.FECHADA, StatusComanda.CANCELADA] for comanda in obj.comandas):
            #     raise ValueError("Mesa possui comandas ativas e não pode ser removida.")
            db.delete(obj)
            db.commit()
        return obj
    
    # Funções específicas para o fluxo da mesa
    def abrir_mesa(self, db: Session, *, mesa_id: uuid.UUID, id_cliente_associado: Optional[uuid.UUID] = None) -> Tuple[Optional[Mesa], Optional[uuid.UUID], Optional[str]]:
        """
        Abre uma mesa, muda seu status para OCUPADA e cria uma nova comanda para ela.
        Retorna (Mesa, id_comanda_ativa, mensagem_erro).
        """
        mesa = self.get(db, id=mesa_id)
        if not mesa:
            return None, None, "Mesa não encontrada."
        
        if mesa.status == StatusMesa.OCUPADA:
            # Tentar encontrar uma comanda ativa para esta mesa
            # comanda_ativa = crud_comanda.comanda.get_comanda_ativa_by_mesa(db, mesa_id=mesa.id)
            # if comanda_ativa:
            #     return mesa, comanda_ativa.id, "Mesa já está ocupada e possui uma comanda ativa."
            # else: # Mesa ocupada mas sem comanda ativa (estado inconsistente, tentar criar uma nova)
            pass # Permite criar nova comanda se não houver uma ativa

        elif mesa.status != StatusMesa.DISPONIVEL and mesa.status != StatusMesa.FECHADA:
             return mesa, None, f"Mesa está {mesa.status} e não pode ser aberta."

        mesa.status = StatusMesa.OCUPADA
        if id_cliente_associado:
            mesa.id_cliente_associado = id_cliente_associado
        
        # Criar uma nova comanda para esta mesa
        # id_comanda_nova = crud_comanda.comanda.create_comanda_para_mesa(db, mesa_id=mesa.id, id_cliente=id_cliente_associado)
        # A lógica de criação da comanda será implementada em crud_comanda.py
        # Por enquanto, vamos simular a criação e retornar um placeholder para o ID da comanda.
        # Esta parte será integrada quando crud_comanda for implementado.
        id_comanda_nova_placeholder = uuid.uuid4() # Placeholder

        db.add(mesa)
        db.commit()
        db.refresh(mesa)
        
        # Publicar evento no Redis sobre a abertura da mesa
        # await redis_client.publish_message(f"mesa_{mesa.id}_status", json.dumps({"status": "OCUPADA", "comanda_id": str(id_comanda_nova_placeholder)}))

        return mesa, id_comanda_nova_placeholder, None

    def fechar_mesa(self, db: Session, *, mesa_id: uuid.UUID) -> Tuple[Optional[Mesa], Optional[str]]:
        """
        Fecha uma mesa, mudando seu status para FECHADA (após pagamento da comanda).
        Retorna (Mesa, mensagem_erro).
        """
        mesa = self.get(db, id=mesa_id)
        if not mesa:
            return None, "Mesa não encontrada."
        
        # Idealmente, verificar se a comanda associada está totalmente paga antes de fechar a mesa.
        # comanda_ativa = crud_comanda.comanda.get_comanda_ativa_by_mesa(db, mesa_id=mesa.id)
        # if comanda_ativa and comanda_ativa.status_comanda != StatusComanda.PAGA_TOTALMENTE:
        #     return mesa, "Comanda da mesa não está totalmente paga."

        mesa.status = StatusMesa.FECHADA # Ou DISPONIVEL, dependendo da regra de negócio
        # mesa.id_cliente_associado = None # Opcional: desassociar cliente ao fechar
        db.add(mesa)
        db.commit()
        db.refresh(mesa)

        # Publicar evento no Redis
        # await redis_client.publish_message(f"mesa_{mesa.id}_status", json.dumps({"status": "FECHADA"}))

        return mesa, None

mesa = CRUDMesa()

