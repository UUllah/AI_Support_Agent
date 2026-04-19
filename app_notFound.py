from fastapi import FastAPI
from pydantic import BaseModel
from embeddings import create_embeddings
from vector_store import load_index, search

app = FastAPI()

index, documents = load_index()

class Question(BaseModel):
    question: str


@app.post("/ask")

def ask(q: Question):

    query_embedding = create_embeddings([q.question])

    results = search(index, documents, query_embedding)

    context = "\n\n".join(results)

    answer = f"""
Based on previous support tickets:

{context}

Suggested troubleshooting steps may include checking firewall rules,
database connectivity, and configuration parameters.
"""

    return {"answer": answer}