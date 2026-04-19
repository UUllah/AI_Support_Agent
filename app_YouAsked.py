# app.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from knowledge_loader import load_ticket_conversations

app = FastAPI()

class Message(BaseModel):
    user_input: str

@app.get("/")
def read_root():
    return {"message": "AI Support Agent is running!"}

@app.post("/chat")
def chat(message: Message):
    # For now, echo back the input
    user_input = message.user_input
    return {"response": f"You said: {user_input}"}