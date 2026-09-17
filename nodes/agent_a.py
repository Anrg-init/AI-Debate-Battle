from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from state.state import DebateState
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
import os
from pathlib import Path
from tools.tools import search_tool

load_dotenv()

llm_a_base = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("Gemini_init_agent_a_key"),
    temperature=0.4
)
llm_a = llm_a_base.bind_tools([search_tool])

FALLBACK_TEXT = "[Agent A could not respond this round due to a technical error]"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "agent_a.md"


def _load_agent_a_prompts():
    """Load the normal and document-grounded prompts from the Markdown file."""
    prompt_file = PROMPT_PATH.read_text(encoding="utf-8")
    no_documents, with_documents = prompt_file.split("## With Documents", maxsplit=1)
    return (
        no_documents.split("## No Documents", maxsplit=1)[1].strip(),
        with_documents.strip(),
    )


AGENT_A_PROMPT, AGENT_A_RAG_PROMPT = _load_agent_a_prompts()


def agent_a_node(state: DebateState) -> dict:
    """Generate Agent A's FOR argument and append it to the debate history."""

    def get_last(history, empty_msg):
        """Return the last successful argument or a fallback message."""
        if history and not history[-1].get("failed"):
            return history[-1]["argument"]
        return empty_msg

    if not state["has_documents"]:
        system_prompt = AGENT_A_PROMPT

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
        system_prompt = AGENT_A_RAG_PROMPT

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