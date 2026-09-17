from dotenv import load_dotenv
from state.state import DebateState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from pathlib import Path
from pydantic import BaseModel


load_dotenv()


class referre_response(BaseModel):
    agent_a_summary: str
    agent_b_summary: str


# Initialize Gemini LLM
llm_referee = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("Gemini_Electronic_Referree_key"),
    temperature=0.4
).with_structured_output(referre_response)
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "agent_referre.md"
REFEREE_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").split(
    "# Referee Prompt",
    maxsplit=1,
)[1].strip()



def agent_referre_node(state: DebateState) -> dict:
    """Summarize both debate positions without declaring a winner."""
    system_prompt = REFEREE_PROMPT


    user_message = f"""Question: {state['user_input']}

    
    questions: {state["user_input"]}
    question_type: {state["input_type"]}

    Agent A's full history: {state['agent_a_history']}
    Agent B's full history: {state['agent_b_history']}



Give a summary for each agent."""

    try:
        result = llm_referee.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        return {
            "agent_a_summary": result.agent_a_summary,
            "agent_b_summary": result.agent_b_summary
        }
    except Exception as e:
        print(f"[agent_referre_node] LLM call failed: {e}")
        return {
            "agent_a_summary": "Referee summary unavailable due to a technical error.",
            "agent_b_summary": "Referee summary unavailable due to a technical error."
        }

