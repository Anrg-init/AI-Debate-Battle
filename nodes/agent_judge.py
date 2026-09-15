from langchain_groq import ChatGroq
from pydantic import BaseModel
from dotenv import load_dotenv
from state.state import DebateState
from langchain_core.messages import HumanMessage, SystemMessage
import os

load_dotenv()


class JudgeDecision(BaseModel):
    winner: str
    reasoning: str
    final_answer: str


llm_judge = ChatGroq(

    model_name="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY_init_judge"),
    temperature=0.4

).with_structured_output(JudgeDecision)



def agent_judge_node(state: DebateState) -> dict:

    system_prompt = """You are the Judge of a debate. You receive the original question, its type (factual/opinion), and summaries of Agent A's and Agent B's cases.

Evaluate based on:
1. Rebuttal Effectiveness — did they address the opponent's key claims, or drop them?
2. Argument Strength & Evidence — logical reasoning vs. bare assertion.
3. Logical Consistency — no self-contradiction or fallacies.
4. Topic Adherence — stayed on topic, proved relevance.
5. Persuasiveness — clarity and precision.

Decision rule based on input_type:
- If "factual": weigh evidence and logical accuracy heavily — there should usually be a clear correct side.
- If "opinion": weigh reasoning strength and persuasiveness — not "truth," since it's subjective.

Give:
1. winner: "Agent A", "Agent B", or "Tie" (only if genuinely balanced)
2. reasoning: concise justification covering the criteria above
3. final_answer: the best answer to the original question, considering both sides

Respond in the structured format only."""


    user_message = f"""Question: {state['user_input']}
Input type: {state['input_type']}

Agent A's summary: {state['agent_a_summary']}

Agent B's summary: {state['agent_b_summary']}

Give your final decision."""

    try:

        result = llm_judge.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        return {
            "judge_final_decision": {
                "winner": result.winner,
                "reasoning": result.reasoning,
                "final_answer": result.final_answer
            }
        }
    except Exception as e:
        print(f"[agent_judge_node] LLM call failed: {e}")

        return{
            "judge_final_decision": {
                "winner": "Undetermined",
                "reasoning": "Judge could not reach a decision due to a technical error.",
                "final_answer": "Unable to generate a final answer due to a technical error."
            }
        }

    


