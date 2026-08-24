from langgraph.graph import START, END, StateGraph
from nodes.clar import clarifier_node, route_after_clarifier, ask_retry_input_node, route_of_agentsloops
from nodes.agent_a import agent_a_node
from nodes.agent_b import agent_b_node
from state.state import DebateState
from nodes.agent_referre import agent_referre_node
from nodes.agent_judge import agent_judge_node

graph = StateGraph(DebateState)

graph.add_node("clarifier", clarifier_node)
graph.add_node("ask_retry_input", ask_retry_input_node)
graph.add_node("agent_a", agent_a_node)
graph.add_node("agent_b", agent_b_node)
graph.add_node("agent_referre", agent_referre_node)
graph.add_node("agent_judge", agent_judge_node)

graph.add_edge(START, "clarifier")
graph.add_conditional_edges("clarifier", route_after_clarifier,{
    "valid": "agent_a",
    "stop": END,
    "retry": "ask_retry_input"
}
)


graph.add_edge("ask_retry_input", "clarifier")


graph.add_edge("agent_a", "agent_b")
graph.add_conditional_edges("agent_b", route_of_agentsloops, {
    "stop": "agent_referre",
    "continue": "agent_a"
})

graph.add_edge("agent_referre", "agent_judge")
graph.add_edge("agent_judge", END)


app = graph.compile()
