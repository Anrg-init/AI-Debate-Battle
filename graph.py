from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from nodes.clar import clarifier_node, route_after_clarifier, route_of_agentsloops
from nodes.agent_a import agent_a_node
from nodes.agent_b import agent_b_node
from state.state import DebateState
from nodes.agent_referre import agent_referre_node
from nodes.agent_judge import agent_judge_node
from nodes.retrieve_context import retrieve_context_node
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

password = os.getenv("DB_PASSWORD") or os.getenv("SUPABASE_DB_PASSWORD", "")
encoded_password = quote(password, safe="")
DB_URI = os.getenv(
    "SUPABASE_DB_URI",
    (
        f"postgresql://{os.getenv('DB_USER', 'postgres.pwtmxzeanmddfftddzhi')}:{encoded_password}"
        f"@{os.getenv('DB_HOST', 'aws-0-ap-northeast-2.pooler.supabase.com')}"
        f":{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}?sslmode=require"
    ),
)

graph = StateGraph(DebateState)

graph.add_node("clarifier", clarifier_node)
graph.add_node("agent_a", agent_a_node)
graph.add_node("agent_b", agent_b_node)
graph.add_node("agent_referre", agent_referre_node)
graph.add_node("agent_judge", agent_judge_node)
graph.add_node("retrieve_context", retrieve_context_node)

graph.add_edge(START, "clarifier")
graph.add_conditional_edges("clarifier", route_after_clarifier, {
    "no_docs": "agent_a",
    "with_docs": "retrieve_context",
    "stop": END
})

graph.add_edge("retrieve_context", "agent_a")
graph.add_edge("agent_a", "agent_b")
graph.add_conditional_edges("agent_b", route_of_agentsloops, {
    "stop": "agent_referre",
    "continue": "agent_a"
})

graph.add_edge("agent_referre", "agent_judge")
graph.add_edge("agent_judge", END)


checkpointer = None
try:
    if os.getenv("SUPABASE_DB_URI") or os.getenv("SUPABASE_DB_PASSWORD"):
        checkpointer_cm = PostgresSaver.from_conn_string(DB_URI)
        checkpointer = checkpointer_cm.__enter__()
        checkpointer.setup()
except Exception as exc:
    print(f"Warning: Postgres checkpointer unavailable ({exc}). Falling back to in-memory saver.")
    checkpointer = MemorySaver()

if checkpointer is None:
    checkpointer = MemorySaver()

app = graph.compile(checkpointer=checkpointer)