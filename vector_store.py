import faiss
import numpy as np
import pickle

INDEX_FILE = "data/ticket_index.faiss"
META_FILE = "data/ticket_meta.pkl"

def build_index(embeddings, documents):

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(np.array(embeddings))

    faiss.write_index(index, INDEX_FILE)

    with open(META_FILE, "wb") as f:
        pickle.dump(documents, f)


def load_index():

    index = faiss.read_index(INDEX_FILE)

    with open(META_FILE, "rb") as f:
        documents = pickle.load(f)

    return index, documents


def search(index, documents, query_embedding, k=3):

    D, I = index.search(query_embedding, k)

    results = [documents[i] for i in I[0]]

    return results