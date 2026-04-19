#!/usr/bin/env python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print(sys.path)
from knowledge_loader import load_ticket_conversations
from embeddings import create_embeddings
from vector_store import build_index
print("Loading tickets from Jitbit...")

docs = load_ticket_conversations()

print("Generating embeddings...")

embeddings = create_embeddings(docs)

print("Building vector index...")

build_index(embeddings, docs)

print("Index built successfully.")