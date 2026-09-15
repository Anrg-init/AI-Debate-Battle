from dotenv import load_dotenv
from state.state import DebateState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
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



def agent_referre_node(state: DebateState) -> dict:
    system_prompt = """You are a neutral Referee in a debate. You receive the complete round-by-round arguments and sources from Agent A and Agent B.

Your job:
1. Summarize Agent A's overall case, including its main arguments and supporting evidence.
2. Summarize Agent B's overall case in the same way.
3. Identify important claims that were not answered by the opponent.
4. Identify claims supported by sources and claims that are unsupported or weakly supported.
5. Note important contradictions, repeated arguments, or logical gaps.

Rules:
- Stay strictly neutral. Do not declare a winner.
- Judge only what was actually said and the sources provided.
- Do not add new arguments, facts, or evidence.
- Do not assume a source proves a claim; check whether the provided evidence actually supports it.
- Distinguish clearly between facts/evidence and opinions or assertions.
- Cover the full debate, not just the final round."""


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

