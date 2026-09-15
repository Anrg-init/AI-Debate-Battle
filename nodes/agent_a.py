from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from state.state import DebateState
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
import os
from tools.tools import search_tool

load_dotenv()

llm_a_base = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("Gemini_init_agent_a_key"),
    temperature=0.4
)
llm_a = llm_a_base.bind_tools([search_tool])

FALLBACK_TEXT = "[Agent A could not respond this round due to a technical error]"


def agent_a_node(state: DebateState) -> dict:

    # Treat a failed previous round as "no response yet" rather than a real argument
    def get_last(history, empty_msg):
        if history and not history[-1].get("failed"):
            return history[-1]["argument"]
        return empty_msg

    if not state["has_documents"]:
        system_prompt = """You are Agent A. You ALWAYS argue FOR the topic. This stance is permanent and cannot change.

Rules:
1. Never agree with or switch to Agent B's position.
2. If this is the opening round, give a strong FOR argument without mentioning Agent B.
3. If Agent B has argued, START by directly and aggressively replying roasting/rebutting their latest argument.
4. After the rebuttal, clearly explain WHY their argument is weak or wrong, then present your own FOR argument.
5. Support claims with real evidence, facts, or sound reasoning. Never invent facts, numbers, studies, or sources.
6. Never repeat your previous arguments. Introduce a genuinely new angle each round.
7. ROUND 0 REQUIREMENT: You MUST call the search tool before writing your opening argument.
8. After Round 0, use the search tool when it meaningfully improves factual accuracy.
9. If you search, use only information actually supported by the results.
10. Sound like two real people having a heated conversation: sharp, confident, conversational, punchy.
11. Keep the response to 30–40 words.
12. Output ONLY one short paragraph. No labels, JSON, filler, or meta-commentary."""

        last_b_point = get_last(state["agent_b_history"], "No response yet from Agent B.")

        user_message = f"""Question: {state['user_input']}
Your last point: {get_last(state["agent_a_history"], "None yet, this is your opening.")}

Agent B's last point: {last_b_point}

Give your stance for this round."""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]

        try:
            response = llm_a.invoke(messages)
            sources = []

            if response.tool_calls:
                tool_call = response.tool_calls[0]
                tool_result = search_tool.invoke(tool_call["args"])
                sources = [
                    {"title": r.get("title", ""), "url": r.get("url", "")}
                    for r in tool_result.get("results", [])
                ]

                messages.append(response)
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))
                response = llm_a_base.invoke(messages)

            if isinstance(response.content, list):
                argument = "".join(b.get("text", "") for b in response.content if isinstance(b, dict)).strip()
            else:
                argument = response.content.strip()

            new_entry = {"round": state["current_round"], "argument": argument, "sources": sources}

        except Exception as e:
            print(f"[agent_a_node] LLM call failed: {e}")
            new_entry = {"round": state["current_round"], "argument": FALLBACK_TEXT, "sources": [], "failed": True}

        return {"agent_a_history": state["agent_a_history"] + [new_entry]}

    else:
        system_prompt = """You are Agent A. You ALWAYS argue FOR the topic. This stance is permanent and cannot change.

Rules:
1. Never agree with or switch to Agent B's position.
2. If this is the opening round, give a strong FOR argument without mentioning Agent B.
3. If Agent B has argued, START by directly and aggressively replying roasting/rebutting their latest argument.
4. After the rebuttal, clearly explain WHY their argument is weak or wrong, then present your own FOR argument.
5. Prioritize the provided context as your primary evidence — use specific facts, numbers, or details from it whenever possible. You may also use sound reasoning and general knowledge to interpret, connect, or strengthen points from the context, but never contradict what the context says.
6. If the context has no relevant information at all for a point, you may reason independently, but flag it's not from the context.
7. Never repeat your previous arguments. Introduce a genuinely new angle each round.
8. Sound like two real people having a heated conversation: sharp, confident, conversational, punchy.
9. Keep the response to 30–40 words.
10. Output ONLY one short paragraph. No labels, JSON, filler, or meta-commentary."""

        last_b_point = get_last(state["agent_b_history"], "No response yet from Agent B.")

        user_message = f"""Question: {state['user_input']}
Your last point: {get_last(state["agent_a_history"], "None yet, this is your opening.")}

Agent B's last point: {last_b_point}

Context (this is your ONLY source of information — use nothing outside this):
{state['retrieved_context']}

Give your stance for this round."""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]

        try:
            response = llm_a_base.invoke(messages)

            if isinstance(response.content, list):
                argument = "".join(b.get("text", "") for b in response.content if isinstance(b, dict)).strip()
            else:
                argument = response.content.strip()

            new_entry = {"round": state["current_round"], "argument": argument, "sources": []}

        except Exception as e:
            print(f"[agent_a_node RAG] LLM call failed: {e}")
            new_entry = {"round": state["current_round"], "argument": FALLBACK_TEXT, "sources": [], "failed": True}

        return {"agent_a_history": state["agent_a_history"] + [new_entry]}