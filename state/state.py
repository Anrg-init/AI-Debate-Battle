from typing import TypedDict

class DebateState(TypedDict):
    user_input: str
    input_type: str              # "factual" or "opinion"
    is_valid: bool
    clarifier_attempts: int

    agent_a_history: list[dict]  # each dict: {"round": int, "argument": str, "sources": list[dict]}
    agent_b_history: list[dict]

    current_round: int

    agent_a_summary: str
    agent_b_summary: str

    judge_final_decision: dict   # {"winner": str, "reasoning": str, "final_answer": str}