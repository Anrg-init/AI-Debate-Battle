from state.state import DebateState
from rag.store import get_vector_store


def retrieve_context_node(state: DebateState) -> dict:
    user_query = state["user_input"]

    vector_store = get_vector_store()

    docs = vector_store.similarity_search(query=user_query, k=5)
    retrieved_text = "\n\n".join(doc.page_content for doc in docs)

    return {"retrieved_context": retrieved_text}