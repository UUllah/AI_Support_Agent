# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from knowledge_loader import load_ticket_conversations
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

app = FastAPI(title="AI Support Agent")

# --------------------------
# Load tickets and build FAISS index
# --------------------------
print("Loading tickets from Jitbit...")
tickets = load_ticket_conversations()
print(f"Loaded {len(tickets)} ticket conversations.")

# Initialize sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode all tickets
print("Encoding tickets...")
ticket_embeddings = model.encode(tickets, convert_to_numpy=True, show_progress_bar=True)

# Build FAISS index
dimension = ticket_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(ticket_embeddings)
print("FAISS index built!")

# --------------------------
# Request body
# --------------------------
class Message(BaseModel):
    user_input: str

# --------------------------
# Endpoints
# --------------------------
@app.get("/")
def read_root():
    return {"message": "AI Support Agent is running!"}

@app.post("/chat")
def chat(message: Message):
    query = message.user_input
    query_embedding = model.encode([query], convert_to_numpy=True)

    # Search FAISS index for top 3 similar tickets
    D, I = index.search(query_embedding, k=3)
    results = [tickets[i] for i in I[0]]

    response = "\n---\n".join(results)
    return {"response": response}