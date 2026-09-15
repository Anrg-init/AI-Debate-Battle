import os

from langchain_community.document_loaders import (
    TextLoader,
    Docx2txtLoader,
    PyMuPDFLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


# ---- Step 1: Load ----
# Reads a PDF/DOCX/TXT file and lazily yields Document objects (raw text + metadata).
def load_document(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif ext == ".docx":
        loader = Docx2txtLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    for document in loader.lazy_load():
        yield document


# ---- Step 2: Chunk ----
# Splits documents into overlapping ~800-char pieces so retrieval is precise
# and context isn't lost at chunk boundaries.
def chunk_document(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )
    return splitter.split_documents(list(documents))  # list() consumes the generator


# ---- Step 3: Embed + Store ----
# embedding_model loaded once at import time (loading it repeatedly is slow).
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model



def build_vector_store(chunks):
    return FAISS.from_documents(chunks, get_embedding_model())

