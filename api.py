from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent.agent import process_user_input
from agent.memory import (init_db, get_pending_plan, get_messages, clear_pending_plan)

init_db()

app = FastAPI(title="Orbia API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
    response = process_user_input(message.message)
    pending_plan = get_pending_plan()

    return {
        "response": response,
        "events": pending_plan or []
    }

@app.post("/approve")
def approve():
    pending_plan = get_pending_plan()

    if not pending_plan:
        return {
            "success": False,
            "message": "Nenhum cronograma pendente."
        }

    response = process_user_input("sim")

    remaining_plan = get_pending_plan()

    if remaining_plan:
        return {
            "success": False,
            "message": response
        }

    return {
        "success": True,
        "response": response
    }

@app.post("/cancel")
def cancel():
    pending_plan = get_pending_plan()

    if not pending_plan:
        return {
            "success": False,
            "message": "Nenhum cronograma pendente."
        }

    clear_pending_plan()

    return {
        "success": True,
        "response": "Tudo bem. O cronograma foi cancelado."
    }

@app.get("/history")
def history():
    messages = get_messages()

    chat_history = []

    for message in messages:
        message_type = message.get("type")
        data = message.get("data", {})

        if message_type == "user_input":
            content = ""

            for item in data.get("content", []):
                if item.get("type") == "text":
                    content += item.get("text", "")

            if content:
                chat_history.append({
                    "role": "user",
                    "content": content
                })

        elif message_type == "model_output":
            content = ""

            if "text" in data:
                content = data["text"]

            elif "content" in data:
                if isinstance(data["content"], str):
                    content = data["content"]

                elif isinstance(data["content"], list):
                    for item in data["content"]:
                        if isinstance(item, dict):
                            content += item.get("text", "")

            if content:
                chat_history.append({
                    "role": "orbia",
                    "content": content
                })

    return {
        "messages": chat_history,
        "pending_plan": get_pending_plan()
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000
    )