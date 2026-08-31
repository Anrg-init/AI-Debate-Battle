# Simple global holder for the current session's vector store.

current_vector_store = None


def set_vector_store(vs):
    global current_vector_store
    current_vector_store = vs


def get_vector_store():
    return current_vector_store