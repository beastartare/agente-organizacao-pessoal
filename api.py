from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent.agent import process_user_input
from agent.memory import (
    init_db,
    get_pending_plan
)


# Inicializa o banco de dados
init_db()


app = FastAPI(title="Orbia API")


# Permite que a extensão se comunique com o servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    message: str


@app.get("/")
def home():

    return {
        "status": "online",
        "message": "Orbia está funcionando."
    }



@app.post("/chat")
def chat(message: Message):

    response = process_user_input(
        message.message
    )

    # Verifica se o Orbia possui uma proposta
    # de eventos aguardando aprovação
    pending_plan = get_pending_plan()

    return {
        "response": response,
        "events": pending_plan or []
    }


# ==========================================
# APROVAÇÃO DO CRONOGRAMA
# ==========================================

@app.post("/approve")
def approve():

    pending_plan = get_pending_plan()

    if not pending_plan:

        return {
            "success": False,
            "message": "Nenhum cronograma pendente."
        }


    # Utiliza a mesma lógica de confirmação
    # que já existe no agent.py
    response = process_user_input("sim")


    return {
        "success": True,
        "response": response
    }


if __name__ == "__main__":

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000
    )