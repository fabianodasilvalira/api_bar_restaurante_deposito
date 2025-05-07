from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_, and_
from . import models, schemas, auth
import uuid
import qrcode
import io
from decimal import Decimal
from datetime import datetime, timezone

# --- User CRUD ---
def get_user(db: Session, user_id: uuid.UUID):
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Usuario).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UsuarioInternoCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.Usuario(
        email=user.email,
        hashed_password=hashed_password,
        nome_completo=user.nome_completo,
        cargo=user.cargo,
        ativo=user.ativo
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Product CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate):
    db_produto = models.Produto(**produto.model_dump())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto

def get_produto(db: Session, produto_id: uuid.UUID):
    return db.query(models.Produto).filter(models.Produto.id == produto_id).first()

def get_produtos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Produto).offset(skip).limit(limit).all()

# --- Cliente CRUD ---
def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    db_cliente = models.Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def get_cliente(db: Session, cliente_id: uuid.UUID):
    return db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

def get_clientes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Cliente).offset(skip).limit(limit).all()

def update_cliente(db: Session, cliente_id: uuid.UUID, cliente_update: schemas.ClienteCreate):
    db_cliente = get_cliente(db, cliente_id)
    if not db_cliente:
        return None
    for key, value in cliente_update.model_dump(exclude_unset=True).items():
        setattr(db_cliente, key, value)
    db_cliente.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

# --- Mesa CRUD ---
def generate_qr_code_hash(mesa_id: uuid.UUID) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mesa_{mesa_id}_{datetime.now(timezone.utc).timestamp()}"))

def create_mesa(db: Session, mesa: schemas.MesaCreate, id_usuario_responsavel: uuid.UUID):
    existing_mesa = db.query(models.Mesa).filter(models.Mesa.numero_identificador == mesa.numero_identificador).first()
    if existing_mesa:
        raise ValueError(f"Mesa com número identificador \'{mesa.numero_identificador}\' já existe.")

    qr_hash = generate_qr_code_hash(uuid.uuid4())
    db_mesa = models.Mesa(
        numero_identificador=mesa.numero_identificador,
        id_cliente_associado=mesa.id_cliente_associado,
        qr_code_hash=qr_hash,
        status="Livre",
        id_usuario_responsavel=id_usuario_responsavel
    )
    db.add(db_mesa)
    db.commit()
    db.refresh(db_mesa)
    return db_mesa

def get_mesa(db: Session, mesa_id: uuid.UUID):
    return db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()

def get_mesa_by_qr_hash(db: Session, qr_code_hash: str):
    return db.query(models.Mesa).filter(models.Mesa.qr_code_hash == qr_code_hash).first()

def get_mesas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Mesa).offset(skip).limit(limit).all()

def open_mesa_and_create_comanda(db: Session, mesa_id: uuid.UUID, id_usuario_responsavel: uuid.UUID, id_cliente_associado: Optional[uuid.UUID] = None):
    db_mesa = get_mesa(db, mesa_id)
    if not db_mesa:
        return None, "Mesa não encontrada"
    
    active_comanda = get_comanda_ativa_by_mesa_id(db, mesa_id=db_mesa.id)
    if active_comanda and db_mesa.status == "Ocupada":
        return db_mesa, "Mesa já está aberta com uma comanda ativa."

    db_mesa.status = "Ocupada"
    db_mesa.data_abertura = func.now()
    db_mesa.id_usuario_responsavel = id_usuario_responsavel
    if id_cliente_associado:
        db_mesa.id_cliente_associado = id_cliente_associado

    if not active_comanda:
        db_comanda = models.Comanda(id_mesa=db_mesa.id, status_pagamento="Pendente")
        db.add(db_comanda)
    else:
        db_comanda = active_comanda

    db.commit()
    db.refresh(db_mesa)
    if db_comanda: db.refresh(db_comanda)
    return db_mesa, "Mesa aberta e comanda criada/associada com sucesso."

# --- Comanda CRUD ---
def get_comanda_ativa_by_mesa_id(db: Session, mesa_id: uuid.UUID):
    return db.query(models.Comanda).filter(
        models.Comanda.id_mesa == mesa_id,
        models.Comanda.status_pagamento.notin_(["Totalmente Pago", "Fiado Fechado"])
    ).order_by(models.Comanda.data_criacao.desc()).first()

def get_comanda_by_id(db: Session, comanda_id: uuid.UUID):
    return db.query(models.Comanda).filter(models.Comanda.id == comanda_id).first()

# --- Pedido CRUD ---
def create_pedido(db: Session, comanda_id: uuid.UUID, pedido_create: schemas.PedidoCreate, id_usuario_solicitante: Optional[uuid.UUID] = None):
    db_comanda = get_comanda_by_id(db, comanda_id)
    if not db_comanda or db_comanda.status_pagamento in ["Totalmente Pago", "Fiado Fechado"]:
        return None, "Comanda não encontrada ou fechada"

    db_pedido = models.Pedido(
        id_comanda=comanda_id,
        tipo=pedido_create.tipo,
        observacoes=pedido_create.observacoes,
        id_usuario_solicitante=id_usuario_solicitante,
        status="Em preparo"
    )
    db.add(db_pedido)
    db.flush()

    total_pedido = Decimal("0.0")
    items_to_add = []
    for item_create in pedido_create.itens:
        db_produto = get_produto(db, item_create.id_produto)
        if not db_produto or not db_produto.disponivel:
            db.rollback()
            return None, f"Produto {item_create.id_produto} não encontrado ou indisponível"
        
        subtotal = db_produto.preco_unitario * item_create.quantidade
        db_item_pedido = models.ItemPedido(
            id_pedido=db_pedido.id,
            id_produto=item_create.id_produto,
            quantidade=item_create.quantidade,
            preco_unitario_momento=db_produto.preco_unitario,
            subtotal=subtotal,
            observacoes_item=item_create.observacoes_item
        )
        items_to_add.append(db_item_pedido)
        total_pedido += subtotal
    
    db.add_all(items_to_add)
    db_comanda.valor_total = (db_comanda.valor_total or Decimal("0.0")) + total_pedido
    db.commit()
    db.refresh(db_pedido)
    db.refresh(db_pedido, attribute_names=["itens_pedido"])
    for item in db_pedido.itens_pedido:
        db.refresh(item, attribute_names=["produto"])
    db.refresh(db_comanda)
    return db_pedido, "Pedido criado com sucesso"

def update_pedido_status(db: Session, pedido_id: uuid.UUID, status_novo: str, current_user: models.Usuario):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not db_pedido:
        return None, "Pedido não encontrado"
    
    allowed_transitions = {
        "Em preparo": ["Entregue", "Saiu para entrega", "Cancelado"],
        "Saiu para entrega": ["Entregue", "Cancelado"],
    }

    if db_pedido.status in ["Entregue", "Cancelado"]:
        return None, f"Pedido já está {db_pedido.status} e não pode ser alterado."

    if status_novo not in allowed_transitions.get(db_pedido.status, []):
        return None, f"Não é possível mudar status de \'{db_pedido.status}\' para \'{status_novo}\'."

    db_pedido.status = status_novo
    db_pedido.data_ultima_atualizacao_status = func.now()
    db.commit()
    db.refresh(db_pedido)
    return db_pedido, f"Status do pedido atualizado para {status_novo}"

# --- Pagamento CRUD ---
def create_pagamento(db: Session, comanda_id: uuid.UUID, pagamento_create: schemas.PagamentoCreate, id_usuario_registrou: uuid.UUID):
    db_comanda = get_comanda_by_id(db, comanda_id)
    if not db_comanda or db_comanda.status_pagamento == "Fiado Fechado":
        return None, "Comanda não encontrada ou já fechada como fiado permanentemente."
    
    if db_comanda.status_pagamento == "Totalmente Pago":
        return None, "Comanda já está totalmente paga."

    valor_pagamento = pagamento_create.valor
    if valor_pagamento <= Decimal("0"): 
        return None, "Valor do pagamento deve ser positivo."

    db_pagamento = models.Pagamento(
        id_comanda=comanda_id,
        valor=valor_pagamento,
        metodo_pagamento=pagamento_create.metodo_pagamento,
        observacoes=pagamento_create.observacoes,
        id_usuario_registrou=id_usuario_registrou
    )
    db.add(db_pagamento)

    db_comanda.valor_pago = (db_comanda.valor_pago or Decimal("0.0")) + valor_pagamento
    
    saldo_devedor = db_comanda.valor_total - db_comanda.valor_pago

    if saldo_devedor <= Decimal("0"): # Consider small tolerance for float issues if not using Decimal for all calcs
        db_comanda.status_pagamento = "Totalmente Pago"
        db_comanda.valor_fiado = Decimal("0.0") # Ensure fiado is zeroed if fully paid
        # Fechar a mesa associada se o pagamento total for concluído
        if db_comanda.mesa:
            db_comanda.mesa.status = "Livre"
            db_comanda.mesa.data_fechamento = func.now()
    elif db_comanda.valor_pago > Decimal("0.0"):
        db_comanda.status_pagamento = "Parcialmente Pago"
    
    db.commit()
    db.refresh(db_pagamento)
    db.refresh(db_comanda)
    if db_comanda.mesa: db.refresh(db_comanda.mesa)
    return db_pagamento, "Pagamento registrado com sucesso."

def get_pagamentos_by_comanda_id(db: Session, comanda_id: uuid.UUID):
    return db.query(models.Pagamento).filter(models.Pagamento.id_comanda == comanda_id).all()

# --- Fiado CRUD ---
def create_fiado_from_comanda(db: Session, comanda_id: uuid.UUID, id_cliente: uuid.UUID, id_usuario_responsavel: uuid.UUID):
    db_comanda = get_comanda_by_id(db, comanda_id)
    if not db_comanda:
        return None, "Comanda não encontrada."
    if db_comanda.status_pagamento == "Totalmente Pago":
        return None, "Comanda já está totalmente paga, não pode ser marcada como fiado."
    if db_comanda.status_pagamento == "Fiado Fechado":
        return None, "Comanda já foi fechada como fiado anteriormente."
    
    db_cliente = get_cliente(db, id_cliente)
    if not db_cliente:
        return None, "Cliente não encontrado para registrar o fiado."

    valor_a_fiar = db_comanda.valor_total - (db_comanda.valor_pago or Decimal("0.0"))
    if valor_a_fiar <= Decimal("0.0"):
        return None, "Não há saldo devedor para registrar como fiado. A comanda deve ser paga totalmente."

    db_fiado_existente = db.query(models.Fiado).filter(models.Fiado.id_comanda_origem == comanda_id).first()
    if db_fiado_existente:
        # Atualiza o valor devido se já existe um registro de fiado para essa comanda (ex: pagamento parcial e depois fiado)
        db_fiado_existente.valor_devido = valor_a_fiar
        db_fiado_existente.status = "Pendente" # Garante que está pendente
        db_fiado_existente.data_ultima_atualizacao = func.now()
        db_fiado = db_fiado_existente
    else:
        db_fiado = models.Fiado(
            id_comanda_origem=comanda_id,
            id_cliente=id_cliente,
            valor_devido=valor_a_fiar,
            status="Pendente"
        )
        db.add(db_fiado)

    db_comanda.valor_fiado = valor_a_fiar
    db_comanda.status_pagamento = "Fiado Fechado" # Status final da comanda que gerou o fiado
    
    # Fechar a mesa associada
    if db_comanda.mesa:
        db_comanda.mesa.status = "Livre"
        db_comanda.mesa.data_fechamento = func.now()
        db_comanda.mesa.id_usuario_responsavel = id_usuario_responsavel # Quem fechou a mesa como fiado

    db.commit()
    db.refresh(db_fiado)
    db.refresh(db_comanda)
    if db_comanda.mesa: db.refresh(db_comanda.mesa)
    return db_fiado, "Fiado registrado com sucesso e comanda fechada."

def get_fiados(db: Session, skip: int = 0, limit: int = 100, cliente_id: Optional[uuid.UUID] = None, status: Optional[str] = None):
    query = db.query(models.Fiado)
    if cliente_id:
        query = query.filter(models.Fiado.id_cliente == cliente_id)
    if status:
        query = query.filter(models.Fiado.status == status)
    return query.order_by(models.Fiado.data_criacao.desc()).offset(skip).limit(limit).all()

def get_fiado_by_id(db: Session, fiado_id: uuid.UUID):
    return db.query(models.Fiado).filter(models.Fiado.id == fiado_id).first()

def registrar_pagamento_fiado(db: Session, fiado_id: uuid.UUID, valor_pago: Decimal, metodo_pagamento: str, id_usuario_registrou: uuid.UUID):
    db_fiado = get_fiado_by_id(db, fiado_id)
    if not db_fiado:
        return None, "Registro de fiado não encontrado."
    if db_fiado.status == "Pago Totalmente":
        return None, "Este fiado já foi totalmente pago."
    if valor_pago <= Decimal("0.0"):
        return None, "Valor do pagamento deve ser positivo."

    # Registrar o pagamento (poderia ser uma tabela separada de PagamentosFiado se necessário rastrear múltiplos pagamentos por fiado)
    # Por simplicidade, vamos apenas abater o valor_devido e atualizar o status.
    db_fiado.valor_devido -= valor_pago
    db_fiado.data_ultima_atualizacao = func.now()

    if db_fiado.valor_devido <= Decimal("0.0"):
        db_fiado.status = "Pago Totalmente"
        db_fiado.valor_devido = Decimal("0.0") # Zera para não ficar negativo
    else:
        db_fiado.status = "Pago Parcialmente"
    
    # Opcional: Criar um registro de transação de pagamento para o fiado
    # db_pagamento_fiado = models.PagamentoFiado(id_fiado=fiado_id, valor=valor_pago, metodo=metodo_pagamento, ...)
    # db.add(db_pagamento_fiado)

    db.commit()
    db.refresh(db_fiado)
    return db_fiado, "Pagamento do fiado registrado com sucesso."




from datetime import date, timedelta
from sqlalchemy import extract

# --- Relatórios Fiado CRUD ---
def get_relatorio_fiado(db: Session, data_inicio: date, data_fim: date):
    # Fiados pendentes ou parcialmente pagos criados no período ou que ainda estavam pendentes no início do período
    fiados_no_periodo = (
        db.query(
            models.Fiado.id_cliente,
            models.Cliente.nome.label("nome_cliente"),
            func.sum(models.Fiado.valor_devido).label("valor_total_devido_cliente"),
            func.count(models.Fiado.id).label("quantidade_fiados_pendentes_cliente")
        )
        .join(models.Cliente, models.Fiado.id_cliente == models.Cliente.id)
        .filter(
            models.Fiado.status.in_(["Pendente", "Pago Parcialmente"]),
            or_(
                models.Fiado.data_criacao.between(data_inicio, data_fim + timedelta(days=1) - timedelta(seconds=1)),
                # Criados no período
                and_(
                    models.Fiado.data_criacao < data_inicio,  # Criados antes do período
                    models.Fiado.status.in_(["Pendente", "Pago Parcialmente"])  # E ainda pendentes/parciais no início
                )
            )
        )
        .group_by(models.Fiado.id_cliente, models.Cliente.nome)
        .all()
    )

    detalhes_clientes = []
    total_geral_devido_calculado = Decimal("0.0")
    total_fiados_registrados_calculado = 0

    for fiado_info in fiados_no_periodo:
        detalhes_clientes.append(schemas.RelatorioFiadoItem(
            id_cliente=fiado_info.id_cliente,
            nome_cliente=fiado_info.nome_cliente or "Cliente não informado",
            valor_total_devido=fiado_info.valor_total_devido_cliente,
            quantidade_fiados_pendentes=fiado_info.quantidade_fiados_pendentes_cliente
        ))
        total_geral_devido_calculado += fiado_info.valor_total_devido_cliente
        total_fiados_registrados_calculado += fiado_info.quantidade_fiados_pendentes_cliente  # Isso é a soma dos counts por cliente

    # Para total_fiados_registrados_periodo, talvez seja melhor contar os fiados distintos que se encaixam no critério.
    # A forma como está, soma a contagem de fiados por cliente.
    # Se for o total de *registros* de fiado que contribuem para o relatório:
    count_total_fiados_no_periodo = db.query(func.count(models.Fiado.id)).filter(
        models.Fiado.status.in_(["Pendente", "Pago Parcialmente"]),
        or_(
            models.Fiado.data_criacao.between(data_inicio, data_fim + timedelta(days=1) - timedelta(seconds=1)),
            and_(
                models.Fiado.data_criacao < data_inicio,
                models.Fiado.status.in_(["Pendente", "Pago Parcialmente"])
            )
        )
    ).scalar() or 0

    return schemas.RelatorioFiado(
        periodo_inicio=data_inicio,
        periodo_fim=data_fim,
        total_geral_devido=total_geral_devido_calculado,
        total_fiados_registrados_periodo=count_total_fiados_no_periodo,  # Usando a contagem total de registros
        detalhes_por_cliente=detalhes_clientes
    )
