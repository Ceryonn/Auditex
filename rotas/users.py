from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import obter_db
from models import User
from rotas.auth import obter_usuario_atual

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/me")
def me(
    user: User = Depends(obter_usuario_atual)
    ):
    return {
    "id": user.id,
    "email": user.email,
    "nivel": user.nivel
    }