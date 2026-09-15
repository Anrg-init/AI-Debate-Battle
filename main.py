from state.state import DebateState
from graph import app
import json
from rag.ingest import load_document, chunk_document, build_vector_store
from rag.store import set_vector_store


inputx = """ perfect age to get married """

use_rag = False

# One-time setup: build vector store from the document (only if using RAG)
if use_rag: 
    documents = load_document("48law.pdf")
    chunks = chunk_document(documents)
    vector_store = build_vector_store(chunks)
    set_vector_store(vector_store)


initial_state: DebateState = {
    "user_input": inputx,
    "input_type": "",
    "is_valid": False,
    "clarifier_attempts": 0,
    "agent_a_history": [],
    "agent_b_history": [],
    "current_round": 0,
    "agent_a_summary": "",
    "agent_b_summary": "",
    "judge_final_decision": {},
    "has_documents": use_rag,
    "retrieved_context": ""
}

result = app.invoke(initial_state)

print(result)
# print(json.dumps(result, indent=4, ensure_ascii=False))

# app.get_graph().draw_mermaid_png(output_file_path="graph2.png")