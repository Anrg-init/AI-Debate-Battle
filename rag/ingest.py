import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    TextLoader,
    Docx2txtLoader,
    PyMuPDFLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


load_dotenv()

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
# Splits documents into overlapping ~1500-character pieces so retrieval is precise
# and context isn't lost at chunk boundaries.
def chunk_document(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=100,
    )
    return splitter.split_documents(list(documents))  # list() consumes the generator


# ---- Step 3: Embed + Store ----
# The embedding model is loaded once. The Google integration batches up to 100
# texts per request and splits further when its token limit requires it.
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=os.getenv("Gemini_levan_embedding_api"),
        )
    return _embedding_model



def build_vector_store(chunks):
    print(f"Embedding {len(chunks)} chunks")
    return FAISS.from_documents(chunks, get_embedding_model())

