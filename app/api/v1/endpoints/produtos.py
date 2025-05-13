# app/api/v1/endpoints/produtos.py
from typing import List, Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models # Ajuste os caminhos de importação
from app.api import deps # Ajuste os caminhos de importação
from app.models.usuario import Usuario

router = APIRouter()


@router.post("/", response_model=schemas.Produto, status_code=status.HTTP_201_CREATED)
def create_produto(
        *,
        db: Session = Depends(deps.get_db),
        produto_in: schemas.ProdutoCreate,
        current_user: Usuario = Depends(deps.get_current_active_superuser)  # Remove this if not used
) -> Any:
    """
    Cria um novo produto.
    Apenas superusuários podem realizar esta ação.
    """
    if not current_user:  # Optional: Add a validation for current_user usage
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    produto = crud.produto.create(db=db, obj_in=produto_in)
    # Aqui você poderia publicar uma mensagem no Redis se a criação/atualização de produtos
    # precisar ser notificada em tempo real para algum componente (ex: cardápio digital)
    # Ex: await redis_client.publish_message(channel="produtos_updates", message=f"Produto criado: {produto.id}")
    return produto

@router.get("/", response_model=List[schemas.Produto])
def read_produtos(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    categoria: Optional[str] = None
    # current_user: Usuario = Depends(deps.get_current_active_user) # Listar produtos pode ser público ou exigir login simples
) -> Any:
    """
    Recupera a lista de produtos. Pode ser filtrada por categoria.
    """
    if categoria:
        produtos = crud.produto.get_multi_by_categoria(db, categoria=categoria, skip=skip, limit=limit)
    else:
        produtos = crud.produto.get_multi(db, skip=skip, limit=limit)
    return produtos

@router.get("/{produto_id}", response_model=schemas.Produto)
def read_produto_by_id(
    produto_id: uuid.UUID,
    db: Session = Depends(deps.get_db)
    # current_user: Usuario = Depends(deps.get_current_active_user) # Ver um produto específico pode ser público
) -> Any:
    """
    Recupera um produto pelo seu ID.
    """
    produto = crud.produto.get(db=db, id=produto_id)
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return produto

@router.put("/{produto_id}", response_model=schemas.Produto)
def update_produto(
    *,
    db: Session = Depends(deps.get_db),
    produto_id: uuid.UUID,
    produto_in: schemas.ProdutoUpdate,
    current_user: Usuario = Depends(deps.get_current_active_superuser) # Apenas superusuários podem atualizar produtos
) -> Any:
    """
    Atualiza um produto.
    Apenas superusuários podem realizar esta ação.
    """
    produto = crud.produto.get(db=db, id=produto_id)
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    produto = crud.produto.update(db=db, db_obj=produto, obj_in=produto_in)
    # Publicar no Redis se necessário
    # Ex: await redis_client.publish_message(channel="produtos_updates", message=f"Produto atualizado: {produto.id}")
    return produto

@router.delete("/{produto_id}", response_model=schemas.Produto)
def delete_produto(
    *,
    db: Session = Depends(deps.get_db),
    produto_id: uuid.UUID,
    current_user: Usuario = Depends(deps.get_current_active_superuser) # Apenas superusuários podem deletar produtos
) -> Any:
    """
    Deleta um produto.
    Apenas superusuários podem realizar esta ação.
    """
    produto = crud.produto.get(db=db, id=produto_id)
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    # Considerar soft delete (marcar como indisponível/arquivado) em vez de hard delete
    # if produto.disponivel:
    #     produto_in_update = schemas.ProdutoUpdate(disponivel=False)
    #     produto = crud.produto.update(db=db, db_obj=produto, obj_in=produto_in_update)
    # else:
    #     produto = crud.produto.remove(db=db, id=produto_id)
    # Para este exemplo, vamos usar o remove direto, mas soft delete é geralmente melhor.
    produto_removido = crud.produto.remove(db=db, id=produto_id)
    # Publicar no Redis se necessário
    # Ex: await redis_client.publish_message(channel="produtos_updates", message=f"Produto removido: {produto_id}")
    return produto_removido

