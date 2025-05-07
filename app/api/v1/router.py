# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import auth, produtos, clientes, mesas, comandas, pedidos, pagamentos, relatorios, fiado

api_router_v1 = APIRouter()

api_router_v1.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router_v1.include_router(produtos.router, prefix="/produtos", tags=["Produtos"])
api_router_v1.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router_v1.include_router(mesas.router, prefix="/mesas", tags=["Mesas"])
api_router_v1.include_router(comandas.router, prefix="/comandas", tags=["Comandas"])
api_router_v1.include_router(pedidos.router, prefix="/pedidos", tags=["Pedidos"])
api_router_v1.include_router(pagamentos.router, prefix="/pagamentos", tags=["Pagamentos"])
api_router_v1.include_router(fiado.router, prefix="/fiado", tags=["Fiado"])
api_router_v1.include_router(relatorios.router, prefix="/relatorios", tags=["Relatórios"])

# Adicionar um endpoint raiz para a v1 para verificar se está funcionando
@api_router_v1.get("/", tags=["Root V1"])
async def read_root_v1():
    return {"message": "API V1 Operacional"}

