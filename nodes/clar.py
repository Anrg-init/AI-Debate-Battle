from dotenv import load_dotenv
from state.state import DebateState
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import os
import json


load_dotenv()


# Initialize Groq LLM
llm = ChatGroq(

    model_name="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY_electronic_clar"),
    temperature=0.4

)

# Main clarifier node, clarifies the user input - whether its factual or opionion
def clarifier_node(state: DebateState) -> dict:

    system_prompt = """You are a Clarifier. Given a user's input, decide:
        1. is_valid: true if the input is a meaningful, debatable question or statement. false if it's gibberish, empty, or nonsensical.
        2. input_type:  Determine if it's "factual" (has a verifiable true/false answer) or "opinion" (subjective, debatable).

        Respond ONLY in JSON format like this, nothing else:
        {"is_valid": true, "input_type": "factual"}"""

    response =  llm.invoke([
        SystemMessage(content= system_prompt),
        HumanMessage(content=state["user_input"])
    ])

    result = json.loads(response.content)

    return {
        "input_type": result["input_type"],
        "is_valid": result["is_valid"],
        "clarifier_attempts": state["clarifier_attempts"] + 1
    }


# checking the route after clarifier
def route_after_clarifier(state: DebateState):

    if state["is_valid"]:
        return "valid"
    elif state["clarifier_attempts"] >2:
        return "stop"
    else:
        return "retry"



# retry node
def ask_retry_input_node(state: DebateState) -> dict:
    print(f"Your input wasn't valid. Attempt {state['clarifier_attempts']} of 3.")
    new_input = input("Please enter a valid question: ")

    return {
        "user_input": new_input
    }


#loop of agenta and agentb debating 
def route_of_agentsloops(state: DebateState) -> dict: 
    if state["current_round"]<2:
        return "continue"
    else: 
        print("----- DEBATE ENDS HERE ---------")
        return "stop"
