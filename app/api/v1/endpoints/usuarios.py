from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def read_usuarios_root():
    return {"message": "Usuarios endpoint is active"}

