from dotenv import load_dotenv
from state.state import DebateState
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import os
import json


load_dotenv()



class ClarifierResponse(BaseModel):
    is_valid: bool
    input_type: str


llm = ChatGroq(
    model_name="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY_electronic_clar"),
    temperature=0.4
).with_structured_output(ClarifierResponse)


def clarifier_node(state: DebateState) -> dict:
    if state["clarifier_attempts"] > 0:
        return {
            "input_type": state["input_type"],
            "is_valid": state["is_valid"],
            "clarifier_attempts": state["clarifier_attempts"]
        }

    system_prompt = """You are a Clarifier. Given a user's input, decide:
    1. is_valid: true if the input is a meaningful, debatable question or statement. false if it's gibberish, empty, or nonsensical.
    2. input_type: Determine if it's "factual" (has a verifiable true/false answer) or "opinion" (subjective, debatable)."""

    try:
        result = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_input"])
        ])
        input_type = result.input_type
        is_valid = result.is_valid
    except Exception as e:
        print(f"[clarifier_node] LLM call failed: {e}")
        # Treat failure as invalid input -> triggers retry flow
        input_type = ""
        is_valid = False

    return {
        "input_type": input_type,
        "is_valid": is_valid,
        "clarifier_attempts": state["clarifier_attempts"] + 1
    }


def route_after_clarifier(state: DebateState) -> str:
    if not state["is_valid"]:
        return "stop"

    if state["has_documents"]:
        return "with_docs"
    else:
        return "no_docs"



#loop of agenta and agentb debating 
def route_of_agentsloops(state: DebateState) -> dict: 
    if state["current_round"] < state["rounds"]:
        return "continue"
    else: 
        print("----- DEBATE ENDS HERE ---------")
        return "stop"
