from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from state.state import DebateState
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
import os
from tools.tools import search_tool

load_dotenv()


llm_b_base = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY_565_agent_b"),
    temperature=0.4
)

llm_b = llm_b_base.bind_tools([search_tool])


def agent_b_node(state: DebateState) -> dict:
    system_prompt = """You are Agent B. You ALWAYS argue AGAINST the topic. This stance is permanent and cannot change.

Rules:
1. Never agree with or switch to Agent A's position.
2. If this is the opening round, give a strong AGAINST argument without mentioning Agent A.
3. If Agent A has argued, START by directly and aggressively replying roasting/rebutting their latest argument. Attack their reasoning, claim, evidence, contradiction, or gap — not their personal identity.
4. After the rebuttal, clearly explain WHY their argument is weak or wrong, then present your own AGAINST argument.
5. Support claims with real evidence, facts, or sound reasoning. Never invent facts, numbers, studies, or sources.
6. Never repeat your previous arguments. Introduce a genuinely new angle each round.
7. ROUND 0 REQUIREMENT: You MUST call the search tool before writing your opening argument. Do not answer Round 0 without using the search tool.
8. After Round 0, use the search tool when it meaningfully improves factual accuracy or provides needed current information.
9. If you search, use only information actually supported by the results.
10. Sound like two real people having a heated conversation: sharp, confident, conversational, and punchy — not like an academic essay.
11. Keep the response to 30–40 words.
12. Output ONLY one short paragraph. No labels, JSON, filler, or meta-commentary."""


    last_a_point = (
        state["agent_a_history"][-1]["argument"]
        if state["agent_a_history"]
        else "No response yet from Agent A."
    )

    last_b_point = (
        state["agent_b_history"][-1]["argument"]
        if state["agent_b_history"]
        else "None yet, this is your opening."
    )

    user_message = f"""Question: {state["user_input"]}

Your previous argument:
{last_b_point}

Agent A's latest argument:
{last_a_point}

Current round: {state["current_round"]}

Give your argument for this round."""


    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]

    response = llm_b.invoke(messages)

    sources = []

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_result = search_tool.invoke(tool_call["args"])

        sources = [
            {
                "title": r["title"],
                "url": r["url"]
            }
            for r in tool_result["results"]
        ]

        messages.append(response)
        messages.append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"]
            )
        )

        # Final call — NO tools
        response = llm_b_base.invoke(messages)

    if isinstance(response.content, list):
        argument = "".join(
            block.get("text", "")
            for block in response.content
            if isinstance(block, dict)
            ).strip()
    else:
        argument = response.content.strip()

    new_entry = {
        "round": state["current_round"],
        "argument": argument,
        "sources": sources
    }

    return {
        "agent_b_history": state["agent_b_history"] + [new_entry],
        "current_round": state["current_round"] + 1
    }