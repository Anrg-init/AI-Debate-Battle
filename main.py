from state.state import DebateState
from nodes.clar import clarifier_node
from graph import app
import json


initial_state: DebateState = {
    "user_input": "fskadh",
    "input_type": "",
    "is_valid": False,
    "clarifier_attempts": 0,
    "agent_a_history": [],
    "agent_b_history": [],
    "current_round": 0,
    "agent_a_summary": "",
    "agent_b_summary": "",
    "judge_final_decision": {}
}

result = app.invoke(initial_state)

print(result)
print(json.dumps(result, indent=4, ensure_ascii=False))