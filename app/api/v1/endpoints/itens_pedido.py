from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def read_itens_pedido_root():
    return {"message": "Itens de Pedido endpoint is active"}

