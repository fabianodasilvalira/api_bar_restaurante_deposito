from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from . import models, schemas
import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone


# ======================
# CRUD: Usuário Interno
# ======================
def get_user(db: Session, user_id: uuid.UUID) -> Optional[models.Usuario]:
    """Obtém um usuário pelo ID"""
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.Usuario]:
    """Obtém um usuário pelo email"""
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.Usuario]:
    """Lista todos os usuários com paginação"""
    return db.query(models.Usuario).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UsuarioInternoCreate) -> models.Usuario:
    """Cria um novo usuário"""
    db_user = models.Usuario(
        email=user.email,
        hashed_password=user.hashed_password,  # Já deve vir hasheado
        nome_completo=user.nome_completo,
        cargo=user.cargo,
        ativo=user.ativo
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: uuid.UUID, user_update: schemas.UsuarioInternoUpdate) -> Optional[models.Usuario]:
    """Atualiza um usuário existente"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db_user.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_user)
    return db_user


def deactivate_user(db: Session, user_id: uuid.UUID) -> Optional[models.Usuario]:
    """Desativa um usuário"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    db_user.ativo = False
    db_user.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_user)
    return db_user


# ======================
# CRUD: Produto
# ======================
def create_produto(db: Session, produto: schemas.ProdutoCreate) -> models.Produto:
    """Cria um novo produto"""
    db_produto = models.Produto(**produto.model_dump())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


def get_produto(db: Session, produto_id: uuid.UUID) -> Optional[models.Produto]:
    """Obtém um produto pelo ID"""
    return db.query(models.Produto).filter(models.Produto.id == produto_id).first()


def get_produtos(db: Session, skip: int = 0, limit: int = 100, categoria: Optional[str] = None,
                 disponivel: Optional[bool] = None) -> List[models.Produto]:
    """Lista produtos com filtros e paginação"""
    query = db.query(models.Produto)

    if categoria:
        query = query.filter(models.Produto.categoria == categoria)
    if disponivel is not None:
        query = query.filter(models.Produto.disponivel == disponivel)

    return query.offset(skip).limit(limit).all()


def update_produto(db: Session, produto_id: uuid.UUID, produto_update: schemas.ProdutoUpdate) -> Optional[
    models.Produto]:
    """Atualiza um produto existente"""
    db_produto = get_produto(db, produto_id)
    if not db_produto:
        return None

    update_data = produto_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_produto, key, value)

    db_produto.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_produto)
    return db_produto


def toggle_produto_availability(db: Session, produto_id: uuid.UUID) -> Optional[models.Produto]:
    """Alterna a disponibilidade de um produto"""
    db_produto = get_produto(db, produto_id)
    if not db_produto:
        return None

    db_produto.disponivel = not db_produto.disponivel
    db_produto.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_produto)
    return db_produto


# ======================
# CRUD: Cliente
# ======================
def create_cliente(db: Session, cliente: schemas.ClienteCreate) -> models.Cliente:
    """Cria um novo cliente"""
    db_cliente = models.Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


def get_cliente(db: Session, cliente_id: uuid.UUID) -> Optional[models.Cliente]:
    """Obtém um cliente pelo ID"""
    return db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()


def get_cliente_by_telefone(db: Session, telefone: str) -> Optional[models.Cliente]:
    """Obtém um cliente pelo telefone"""
    return db.query(models.Cliente).filter(models.Cliente.telefone == telefone).first()


def get_clientes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Cliente]:
    """Lista todos os clientes com paginação"""
    return db.query(models.Cliente).offset(skip).limit(limit).all()


def update_cliente(db: Session, cliente_id: uuid.UUID, cliente_update: schemas.ClienteUpdate) -> Optional[
    models.Cliente]:
    """Atualiza um cliente existente"""
    db_cliente = get_cliente(db, cliente_id)
    if not db_cliente:
        return None

    update_data = cliente_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cliente, key, value)

    db_cliente.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


# ======================
# CRUD: Mesa
# ======================
def generate_qr_code_hash(mesa_id: uuid.UUID) -> str:
    """Gera um hash único para QR Code da mesa"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mesa_{mesa_id}_{datetime.now(timezone.utc).timestamp()}"))


def create_mesa(db: Session, mesa: schemas.MesaCreate) -> models.Mesa:
    """Cria uma nova mesa"""
    # Verifica se já existe uma mesa com o mesmo número identificador
    existing_mesa = db.query(models.Mesa).filter(
        models.Mesa.numero_identificador == mesa.numero_identificador
    ).first()

    if existing_mesa:
        raise ValueError(f"Mesa com número '{mesa.numero_identificador}' já existe")

    db_mesa = models.Mesa(
        numero_identificador=mesa.numero_identificador,
        qr_code_hash=generate_qr_code_hash(uuid.uuid4()),
        status="Livre"
    )

    db.add(db_mesa)
    db.commit()
    db.refresh(db_mesa)
    return db_mesa


def get_mesa(db: Session, mesa_id: uuid.UUID) -> Optional[models.Mesa]:
    """Obtém uma mesa pelo ID"""
    return db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()


def get_mesa_by_numero(db: Session, numero: str) -> Optional[models.Mesa]:
    """Obtém uma mesa pelo número identificador"""
    return db.query(models.Mesa).filter(models.Mesa.numero_identificador == numero).first()


def get_mesa_by_qr_hash(db: Session, qr_code_hash: str) -> Optional[models.Mesa]:
    """Obtém uma mesa pelo hash do QR Code"""
    return db.query(models.Mesa).filter(models.Mesa.qr_code_hash == qr_code_hash).first()


def get_mesas(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[models.Mesa]:
    """Lista mesas com filtros e paginação"""
    query = db.query(models.Mesa)

    if status:
        query = query.filter(models.Mesa.status == status)

    return query.offset(skip).limit(limit).all()


def update_mesa_status(db: Session, mesa_id: uuid.UUID, status: str,
                       id_usuario_responsavel: Optional[uuid.UUID] = None) -> Optional[models.Mesa]:
    """Atualiza o status de uma mesa"""
    db_mesa = get_mesa(db, mesa_id)
    if not db_mesa:
        return None

    db_mesa.status = status
    db_mesa.id_usuario_responsavel = id_usuario_responsavel

    if status == "Ocupada":
        db_mesa.data_abertura = func.now()
    elif status == "Livre":
        db_mesa.data_fechamento = func.now()

    db_mesa.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_mesa)
    return db_mesa


def associate_cliente_to_mesa(db: Session, mesa_id: uuid.UUID, cliente_id: uuid.UUID) -> Optional[models.Mesa]:
    """Associa um cliente a uma mesa"""
    db_mesa = get_mesa(db, mesa_id)
    db_cliente = get_cliente(db, cliente_id)

    if not db_mesa or not db_cliente:
        return None

    db_mesa.id_cliente_associado = cliente_id
    db_mesa.data_atualizacao = func.now()
    db.commit()
    db.refresh(db_mesa)
    return db_mesa


# ======================
# CRUD: Comanda
# ======================
def create_comanda(db: Session, mesa_id: uuid.UUID) -> models.Comanda:
    """Cria uma nova comanda para uma mesa"""
    db_mesa = get_mesa(db, mesa_id)
    if not db_mesa:
        raise ValueError("Mesa não encontrada")

    # Verifica se já existe uma comanda ativa para a mesa
    existing_comanda = get_comanda_ativa_by_mesa_id(db, mesa_id)
    if existing_comanda:
        raise ValueError("Já existe uma comanda ativa para esta mesa")

    db_comanda = models.Comanda(
        id_mesa=mesa_id,
        status_pagamento="Pendente"
    )

    db.add(db_comanda)
    db.commit()
    db.refresh(db_comanda)

    # Atualiza o status da mesa para ocupada
    update_mesa_status(db, mesa_id, "Ocupada")

    return db_comanda


def get_comanda(db: Session, comanda_id: uuid.UUID) -> Optional[models.Comanda]:
    """Obtém uma comanda pelo ID"""
    return db.query(models.Comanda).filter(models.Comanda.id == comanda_id).first()


def get_comanda_ativa_by_mesa_id(db: Session, mesa_id: uuid.UUID) -> Optional[models.Comanda]:
    """Obtém a comanda ativa de uma mesa"""
    return db.query(models.Comanda).filter(
        models.Comanda.id_mesa == mesa_id,
        models.Comanda.status_pagamento.notin_(["Totalmente Pago", "Fiado Fechado"])
    ).order_by(models.Comanda.data_criacao.desc()).first()


def get_comandas(db: Session, skip: int = 0, limit: int = 100, status_pagamento: Optional[str] = None) -> List[
    models.Comanda]:
    """Lista comandas com filtros e paginação"""
    query = db.query(models.Comanda)

    if status_pagamento:
        query = query.filter(models.Comanda.status_pagamento == status_pagamento)

    return query.offset(skip).limit(limit).all()


def update_comanda_status(db: Session, comanda_id: uuid.UUID, status: str) -> Optional[models.Comanda]:
    """Atualiza o status de pagamento de uma comanda"""
    db_comanda = get_comanda(db, comanda_id)
    if not db_comanda:
        return None

    db_comanda.status_pagamento = status
    db_comanda.data_atualizacao = func.now()

    # Se a comanda foi totalmente paga ou marcada como fiado, libera a mesa
    if status in ["Totalmente Pago", "Fiado Fechado"]:
        if db_comanda.mesa:
            update_mesa_status(db, db_comanda.mesa.id, "Livre")

    db.commit()
    db.refresh(db_comanda)
    return db_comanda


def calculate_comanda_total(db: Session, comanda_id: uuid.UUID) -> Decimal:
    """Calcula o valor total de uma comanda baseado nos pedidos"""
    db_comanda = get_comanda(db, comanda_id)
    if not db_comanda:
        return Decimal("0.00")

    total = Decimal("0.00")
    for pedido in db_comanda.pedidos:
        for item in pedido.itens_pedido:
            total += item.subtotal

    db_comanda.valor_total = total
    db.commit()
    db.refresh(db_comanda)
    return total


# ======================
# CRUD: Pedido
# ======================
def create_pedido(db: Session, comanda_id: uuid.UUID, pedido_data: schemas.PedidoCreate,
                  id_usuario_solicitante: Optional[uuid.UUID] = None) -> Tuple[Optional[models.Pedido], str]:
    """Cria um novo pedido para uma comanda"""
    db_comanda = get_comanda(db, comanda_id)
    if not db_comanda:
        return None, "Comanda não encontrada"

    if db_comanda.status_pagamento in ["Totalmente Pago", "Fiado Fechado"]:
        return None, "Comanda já está fechada"

    db_pedido = models.Pedido(
        id_comanda=comanda_id,
        tipo=pedido_data.tipo,
        status="Em preparo",
        observacoes=pedido_data.observacoes,
        id_usuario_solicitante=id_usuario_solicitante
    )

    db.add(db_pedido)
    db.flush()  # Para obter o ID do pedido antes do commit

    total_pedido = Decimal("0.00")
    itens_pedido = []

    for item in pedido_data.itens:
        db_produto = get_produto(db, item.id_produto)
        if not db_produto or not db_produto.disponivel:
            db.rollback()
            return None, f"Produto {item.id_produto} não encontrado ou indisponível"

        subtotal = db_produto.preco_unitario * item.quantidade
        db_item = models.ItemPedido(
            id_pedido=db_pedido.id,
            id_produto=item.id_produto,
            quantidade=item.quantidade,
            preco_unitario_momento=db_produto.preco_unitario,
            subtotal=subtotal,
            observacoes_item=item.observacoes_item
        )

        itens_pedido.append(db_item)
        total_pedido += subtotal

    db.add_all(itens_pedido)
    db_comanda.valor_total = (db_comanda.valor_total or Decimal("0.00")) + total_pedido
    db.commit()

    db.refresh(db_pedido)
    return db_pedido, "Pedido criado com sucesso"


def get_pedido(db: Session, pedido_id: uuid.UUID) -> Optional[models.Pedido]:
    """Obtém um pedido pelo ID"""
    return db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()


def get_pedidos_by_comanda(db: Session, comanda_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.Pedido]:
    """Lista pedidos de uma comanda"""
    return db.query(models.Pedido).filter(
        models.Pedido.id_comanda == comanda_id
    ).offset(skip).limit(limit).all()


def update_pedido_status(db: Session, pedido_id: uuid.UUID, novo_status: str) -> Tuple[Optional[models.Pedido], str]:
    """Atualiza o status de um pedido"""
    db_pedido = get_pedido(db, pedido_id)
    if not db_pedido:
        return None, "Pedido não encontrado"

    # Verifica transições válidas de status
    valid_transitions = {
        "Em preparo": ["Saiu para entrega", "Entregue", "Cancelado"],
        "Saiu para entrega": ["Entregue", "Cancelado"],
    }

    if db_pedido.status in ["Entregue", "Cancelado"]:
        return None, f"Pedido já está {db_pedido.status} e não pode ser alterado"

    if novo_status not in valid_transitions.get(db_pedido.status, []):
        return None, f"Transição de {db_pedido.status} para {novo_status} não permitida"

    db_pedido.status = novo_status
    db_pedido.data_ultima_atualizacao_status = func.now()
    db.commit()
    db.refresh(db_pedido)
    return db_pedido, f"Status atualizado para {novo_status}"


def cancel_pedido(db: Session, pedido_id: uuid.UUID) -> Tuple[Optional[models.Pedido], str]:
    """Cancela um pedido"""
    db_pedido = get_pedido(db, pedido_id)
    if not db_pedido:
        return None, "Pedido não encontrado"

    if db_pedido.status == "Cancelado":
        return db_pedido, "Pedido já estava cancelado"

    if db_pedido.status == "Entregue":
        return None, "Pedido já foi entregue e não pode ser cancelado"

    db_pedido.status = "Cancelado"
    db_pedido.data_ultima_atualizacao_status = func.now()

    # Atualiza o valor total da comanda subtraindo os itens cancelados
    if db_pedido.comanda:
        total_cancelado = Decimal("0.00")
        for item in db_pedido.itens_pedido:
            total_cancelado += item.subtotal

        db_pedido.comanda.valor_total -= total_cancelado
        if db_pedido.comanda.valor_total < Decimal("0.00"):
            db_pedido.comanda.valor_total = Decimal("0.00")

    db.commit()
    db.refresh(db_pedido)
    return db_pedido, "Pedido cancelado com sucesso"


# ======================
# CRUD: ItemPedido
# ======================
def get_itens_pedido(db: Session, pedido_id: uuid.UUID) -> List[models.ItemPedido]:
    """Lista itens de um pedido"""
    return db.query(models.ItemPedido).filter(
        models.ItemPedido.id_pedido == pedido_id
    ).all()


def add_item_to_pedido(db: Session, pedido_id: uuid.UUID, item_data: schemas.ItemPedidoCreate) -> Tuple[
    Optional[models.ItemPedido], str]:
    """Adiciona um item a um pedido existente"""
    db_pedido = get_pedido(db, pedido_id)
    if not db_pedido:
        return None, "Pedido não encontrado"

    if db_pedido.status in ["Cancelado", "Entregue"]:
        return None, "Pedido já está fechado ou cancelado"

    db_produto = get_produto(db, item_data.id_produto)
    if not db_produto or not db_produto.disponivel:
        return None, "Produto não encontrado ou indisponível"

    subtotal = db_produto.preco_unitario * item_data.quantidade
    db_item = models.ItemPedido(
        id_pedido=pedido_id,
        id_produto=item_data.id_produto,
        quantidade=item_data.quantidade,
        preco_unitario_momento=db_produto.preco_unitario,
        subtotal=subtotal,
        observacoes_item=item_data.observacoes_item
    )

    db.add(db_item)

    # Atualiza o valor total da comanda
    if db_pedido.comanda:
        db_pedido.comanda.valor_total = (db_pedido.comanda.valor_total or Decimal("0.00")) + subtotal

    db.commit()
    db.refresh(db_item)
    return db_item, "Item adicionado ao pedido com sucesso"


def remove_item_from_pedido(db: Session, item_id: uuid.UUID) -> Tuple[bool, str]:
    """Remove um item de um pedido"""
    db_item = db.query(models.ItemPedido).filter(models.ItemPedido.id == item_id).first()
    if not db_item:
        return False, "Item não encontrado"

    db_pedido = db_item.pedido
    if db_pedido.status in ["Cancelado", "Entregue"]:
        return False, "Pedido já está fechado ou cancelado"

    # Atualiza o valor total da comanda
    if db_pedido.comanda:
        db_pedido.comanda.valor_total -= db_item.subtotal
        if db_pedido.comanda.valor_total < Decimal("0.00"):
            db_pedido.comanda.valor_total = Decimal("0.00")

    db.delete(db_item)
    db.commit()
    return True, "Item removido com sucesso"


# ======================
# CRUD: Pagamento
# ======================
def create_pagamento(db: Session, comanda_id: uuid.UUID, pagamento_data: schemas.PagamentoCreate,
                     id_usuario_registrou: Optional[uuid.UUID] = None) -> Tuple[Optional[models.Pagamento], str]:
    """Registra um pagamento para uma comanda"""
    db_comanda = get_comanda(db, comanda_id)
    if not db_comanda:
        return None, "Comanda não encontrada"

    if db_comanda.status_pagamento in ["Totalmente Pago", "Fiado Fechado"]:
        return None, "Comanda já está fechada"

    if pagamento_data.valor <= Decimal("0.00"):
        return None, "Valor do pagamento deve ser positivo"

    db_pagamento = models.Pagamento(
        id_comanda=comanda_id,
        valor=pagamento_data.valor,
        metodo_pagamento=pagamento_data.metodo_pagamento,
        observacoes=pagamento_data.observacoes,
        id_usuario_registrou=id_usuario_registrou
    )

    db.add(db_pagamento)

    # Atualiza valores na comanda
    db_comanda.valor_pago = (db_comanda.valor_pago or Decimal("0.00")) + pagamento_data.valor

    # Verifica se a comanda foi totalmente paga
    saldo_restante = db_comanda.valor_total - db_comanda.valor_pago

    if saldo_restante <= Decimal("0.00"):
        db_comanda.status_pagamento = "Totalmente Pago"
        db_comanda.valor_fiado = Decimal("0.00")

        # Libera a mesa se existir
        if db_comanda.mesa:
            update_mesa_status(db, db_comanda.mesa.id, "Livre")
    else:
        db_comanda.status_pagamento = "Parcialmente Pago"

    db.commit()
    db.refresh(db_pagamento)
    return db_pagamento, "Pagamento registrado com sucesso"


def get_pagamentos_by_comanda(db: Session, comanda_id: uuid.UUID) -> List[models.Pagamento]:
    """Lista pagamentos de uma comanda"""
    return db.query(models.Pagamento).filter(
        models.Pagamento.id_comanda == comanda_id
    ).order_by(models.Pagamento.data_pagamento).all()


def get_total_pago_comanda(db: Session, comanda_id: uuid.UUID) -> Decimal:
    """Calcula o total pago em uma comanda"""
    total = db.query(func.sum(models.Pagamento.valor)).filter(
        models.Pagamento.id_comanda == comanda_id
    ).scalar()

    return total or Decimal("0.00")


# ======================
# CRUD: Fiado
# ======================
def create_fiado(db: Session, comanda_id: uuid.UUID, cliente_id: uuid.UUID,
                 id_usuario_responsavel: Optional[uuid.UUID] = None) -> Tuple[Optional[models.Fiado], str]:
    """Registra uma comanda como fiado para um cliente"""
    db_comanda = get_comanda(db, comanda_id)
    if not db_comanda:
        return None, "Comanda não encontrada"

    if db_comanda.status_pagamento == "Totalmente Pago":
        return None, "Comanda já está totalmente paga"

    if db_comanda.status_pagamento == "Fiado Fechado":
        return None, "Comanda já foi registrada como fiado"

    db_cliente = get_cliente(db, cliente_id)
    if not db_cliente:
        return None, "Cliente não encontrado"

    valor_fiado = db_comanda.valor_total - (db_comanda.valor_pago or Decimal("0.00"))
    if valor_fiado <= Decimal("0.00"):
        return None, "Não há valor pendente para registrar como fiado"

    # Verifica se já existe um fiado para esta comanda (pode acontecer em caso de atualização)
    existing_fiado = db.query(models.Fiado).filter(
        models.Fiado.id_comanda_origem == comanda_id
    ).first()

    if existing_fiado:
        # Atualiza o fiado existente
        existing_fiado.valor_devido = valor_fiado
        existing_fiado.status = "Pendente"
        existing_fiado.data_ultima_atualizacao = func.now()
        db_fiado = existing_fiado
    else:
        # Cria um novo registro de fiado
        db_fiado = models.Fiado(
            id_comanda_origem=comanda_id,
            id_cliente=cliente_id,
            valor_devido=valor_fiado,
            status="Pendente"
        )
        db.add(db_fiado)

    # Atualiza a comanda
    db_comanda.status_pagamento = "Fiado Fechado"
    db_comanda.valor_fiado = valor_fiado

    # Libera a mesa se existir
    if db_comanda.mesa:
        update_mesa_status(db, db_comanda.mesa.id, "Livre", id_usuario_responsavel)

    db.commit()
    db.refresh(db_fiado)
    return db_fiado, "Fiado registrado com sucesso"


def get_fiado(db: Session, fiado_id: uuid.UUID) -> Optional[models.Fiado]:
    """Obtém um registro de fiado pelo ID"""
    return db.query(models.Fiado).filter(models.Fiado.id == fiado_id).first()


def get_fiados_by_cliente(db: Session, cliente_id: uuid.UUID, status: Optional[str] = None) -> List[models.Fiado]:
    """Lista fiados de um cliente com filtro de status"""
    query = db.query(models.Fiado).filter(
        models.Fiado.id_cliente == cliente_id
    )

    if status:
        query = query.filter(models.Fiado.status == status)

    return query.order_by(models.Fiado.data_criacao.desc()).all()


def get_all_fiados(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[models.Fiado]:
    """Lista todos os fiados com filtros e paginação"""
    query = db.query(models.Fiado)

    if status:
        query = query.filter(models.Fiado.status == status)

    return query.order_by(models.Fiado.data_criacao.desc()).offset(skip).limit(limit).all()


def registrar_pagamento_fiado(db: Session, fiado_id: uuid.UUID, valor_pago: Decimal, metodo_pagamento: str,
                              id_usuario_registrou: Optional[uuid.UUID] = None) -> Tuple[Optional[models.Fiado], str]:
    """Registra um pagamento para um fiado"""
    db_fiado = get_fiado(db, fiado_id)
    if not db_fiado:
        return None, "Fiado não encontrado"

    if db_fiado.status == "Pago Totalmente":
        return None, "Fiado já foi totalmente pago"

    if valor_pago <= Decimal("0.00"):
        return None, "Valor do pagamento deve ser positivo"

    if valor_pago > db_fiado.valor_devido:
        return None, "Valor do pagamento excede o valor devido"

    # Cria um registro de pagamento (opcional, pode ser uma tabela separada)
    db_pagamento = models.Pagamento(
        id_comanda=db_fiado.id_comanda_origem,
        valor=valor_pago,
        metodo_pagamento=metodo_pagamento,
        id_usuario_registrou=id_usuario_registrou,
        observacoes=f"Pagamento de fiado ID: {fiado_id}"
    )
    db.add(db_pagamento)

    # Atualiza o fiado
    db_fiado.valor_devido -= valor_pago

    if db_fiado.valor_devido <= Decimal("0.00"):
        db_fiado.status = "Pago Totalmente"
        db_fiado.valor_devido = Decimal("0.00")
    else:
        db_fiado.status = "Pago Parcialmente"

    db_fiado.data_ultima_atualizacao = func.now()

    # Atualiza a comanda original (opcional)
    db_comanda = db_fiado.comanda_origem
    if db_comanda:
        db_comanda.valor_pago = (db_comanda.valor_pago or Decimal("0.00")) + valor_pago

    db.commit()
    db.refresh(db_fiado)
    return db_fiado, "Pagamento do fiado registrado com sucesso"


# ======================
# Relatórios
# ======================
def get_relatorio_fiados(db: Session, data_inicio: date, data_fim: date) -> schemas.RelatorioFiado:
    """Gera relatório de fiados no período especificado"""
    # Fiados pendentes ou parcialmente pagos criados no período ou que ainda estavam pendentes no início do período
    fiados_no_periodo = (
        db.query(
            models.Fiado.id_cliente,
            models.Cliente.nome.label("nome_cliente"),
            func.sum(models.Fiado.valor_devido).label("valor_total_devido_cliente"),
            func.count(models.Fiado.id).label("quantidade_fiados_cliente")
        )
        .join(models.Cliente, models.Fiado.id_cliente == models.Cliente.id)
        .filter(
            models.Fiado.status.in_(["Pendente", "Pago Parcialmente"]),
            or_(
                models.Fiado.data_criacao.between(data_inicio, data_fim),
                and_(
                    models.Fiado.data_criacao < data_inicio,
                    models.Fiado.status.in_(["Pendente", "Pago Parcialmente"])
                )
            )
        )
        .group_by(models.Fiado.id_cliente, models.Cliente.nome)
        .all()
    )

    detalhes_clientes = []
    total_geral_devido = Decimal("0.00")
    total_fiados = 0

    for fiado_info in fiados_no_periodo:
        detalhes_clientes.append(schemas.RelatorioFiadoItem(
            id_cliente=fiado_info.id_cliente,
            nome_cliente=fiado_info.nome_cliente or "Cliente não informado",
            valor_total_devido=fiado_info.valor_total_devido_cliente,
            quantidade_fiados_pendentes=fiado_info.quantidade_fiados_cliente
        ))
        total_geral_devido += fiado_info.valor_total_devido_cliente
        total_fiados += fiado_info.quantidade_fiados_cliente

    # Contagem total de registros de fiado no período
    total_fiados_registrados = db.query(func.count(models.Fiado.id)).filter(
        models.Fiado.data_criacao.between(data_inicio, data_fim)
    ).scalar() or 0

    return schemas.RelatorioFiado(
        periodo_inicio=data_inicio,
        periodo_fim=data_fim,
        total_geral_devido=total_geral_devido,
        total_fiados_registrados_periodo=total_fiados_registrados,
        total_fiados_pendentes=total_fiados,
        detalhes_por_cliente=detalhes_clientes
    )


def get_relatorio_vendas(db: Session, data_inicio: date, data_fim: date) -> schemas.RelatorioVendas:
    """Gera relatório de vendas no período especificado"""
    # Total de vendas por método de pagamento
    vendas_por_metodo = (
        db.query(
            models.Pagamento.metodo_pagamento,
            func.sum(models.Pagamento.valor).label("total_vendas")
        )
        .filter(models.Pagamento.data_pagamento.between(data_inicio, data_fim))
        .group_by(models.Pagamento.metodo_pagamento)
        .all()
    )

    # Total de vendas
    total_vendas = db.query(func.sum(models.Pagamento.valor)).filter(
        models.Pagamento.data_pagamento.between(data_inicio, data_fim)
    ).scalar() or Decimal("0.00")

    # Total de comandas fechadas
    total_comandas = db.query(func.count(models.Comanda.id)).filter(
        models.Comanda.data_atualizacao.between(data_inicio, data_fim),
        models.Comanda.status_pagamento.in_(["Totalmente Pago", "Fiado Fechado"])
    ).scalar() or 0

    # Produtos mais vendidos
    produtos_mais_vendidos = (
        db.query(
            models.Produto.nome,
            models.Produto.categoria,
            func.sum(models.ItemPedido.quantidade).label("quantidade_vendida"),
            func.sum(models.ItemPedido.subtotal).label("total_vendido")
        )
        .join(models.ItemPedido, models.ItemPedido.id_produto == models.Produto.id)
        .join(models.Pedido, models.ItemPedido.id_pedido == models.Pedido.id)
        .join(models.Comanda, models.Pedido.id_comanda == models.Comanda.id)
        .filter(
            models.Comanda.data_atualizacao.between(data_inicio, data_fim),
            models.Comanda.status_pagamento.in_(["Totalmente Pago", "Fiado Fechado"])
        )
        .group_by(models.Produto.nome, models.Produto.categoria)
        .order_by(func.sum(models.ItemPedido.subtotal).desc())
        .limit(10)
        .all()
    )

    return schemas.RelatorioVendas(
        periodo_inicio=data_inicio,
        periodo_fim=data_fim,
        total_vendas=total_vendas,
        total_comandas=total_comandas,
        vendas_por_metodo=[
            schemas.VendaPorMetodo(
                metodo_pagamento=item.metodo_pagamento,
                total_vendas=item.total_vendas
            ) for item in vendas_por_metodo
        ],
        produtos_mais_vendidos=[
            schemas.ProdutoMaisVendido(
                nome=item.nome,
                categoria=item.categoria,
                quantidade_vendida=item.quantidade_vendida,
                total_vendido=item.total_vendido
            ) for item in produtos_mais_vendidos
        ]
    )