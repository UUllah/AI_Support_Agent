# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from knowledge_loader import load_ticket_conversations
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import re
import openai  # Make sure to pip install openai
import os

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = FastAPI(title="AI Support Agent")

# --------------------------
# Utility functions
# --------------------------
def clean_ticket_text(text):
    # Remove greetings and signatures
    text = re.sub(r"(?i)(dear\s+\w+,)", "", text)
    text = re.sub(r"(?i)(regards,.*)", "", text, flags=re.DOTALL)
    # Remove multiple spaces & HTML entities
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_text(text, max_words=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i+max_words]))
    return chunks
# Replace summarize_tickets function with this
def summarize_tickets(results):
    context = "\n---\n".join(results)
    prompt = f"Summarize the following ticket conversations into a concise and actionable answer:\n{context}"

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
 #       max_tokens=300
    )
    return response.choices[0].message.content
    
    
    
    
#def summarize_tickets(results):
#    context = "\n---\n".join(results)
#    prompt = f"Summarize the following ticket conversations into a concise and actionable answer:\n{context}"
#    response = openai.ChatCompletion.create(
#        model="gpt-3.5-turbo",
#        messages=[{"role": "user", "content": prompt}],
#        max_tokens=300
#    )
#    return response['choices'][0]['message']['content']

# --------------------------
# Load tickets and build FAISS index
# --------------------------
print("Loading tickets from Jitbit...")
tickets_raw = load_ticket_conversations()
print(f"Loaded {len(tickets_raw)} ticket conversations.")

# Clean and chunk tickets
tickets = []
for t in tickets_raw:
    t_clean = clean_ticket_text(t)
    chunks = chunk_text(t_clean, max_words=100)
    tickets.extend(chunks)

print(f"Total chunks for FAISS: {len(tickets)}")

# Sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode tickets
print("Encoding ticket chunks...")
ticket_embeddings = model.encode(tickets, convert_to_numpy=True, show_progress_bar=True)

# FAISS index
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
# API endpoints
# --------------------------
@app.get("/")
def read_root():
    return {"message": "AI Support Agent is running!"}

@app.post("/chat")
def chat(message: Message):
    query = message.user_input
    query_embedding = model.encode([query], convert_to_numpy=True)

    # Search FAISS index for top 3 chunks
    D, I = index.search(query_embedding, k=3)
    results = [tickets[i] for i in I[0]]

    # Summarize with OpenAI GPT
    summary = summarize_tickets(results)

    return {"response": summary}