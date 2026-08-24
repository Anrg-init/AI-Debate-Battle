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





def agent_a_node(state: DebateState) -> dict:
    system_prompt = """You are Agent A. You ALWAYS argue FOR the topic. This stance is permanent and cannot change.

Rules:
1. Never agree with or switch to Agent B's position.
2. If this is the opening round, give a strong FOR argument without mentioning Agent B.
3. If Agent B has argued, START by directly and aggressively replying roasting/rebutting their latest argument. Attack their reasoning, claim, evidence, contradiction, or gap — not their personal identity.
4. After the rebuttal, clearly explain WHY their argument is weak or wrong, then present your own FOR argument.
5. Support claims with real evidence, facts, or sound reasoning. Never invent facts, numbers, studies, or sources.
6. Never repeat your previous arguments. Introduce a genuinely new angle each round.
7. ROUND 0 REQUIREMENT: You MUST call the search tool before writing your opening argument. Do not answer Round 0 without using the search tool.
8. After Round 0, use the search tool when it meaningfully improves factual accuracy or provides needed current information.
9. If you search, use only information actually supported by the results.
10. Sound like two real people having a heated conversation: sharp, confident, conversational, and punchy — not like an academic essay.
11. Keep the response to 30–40 words.
12. Output ONLY one short paragraph. No labels, JSON, filler, or meta-commentary."""




    last_b_point = (
        state["agent_b_history"][-1]["argument"]
        if state["agent_b_history"]
        else "No response yet from Agent B."
    )

    user_message = f"""Question: {state['user_input']}
            
        Your last point: {(
            state["agent_a_history"][-1]["argument"]
            if state["agent_a_history"]
            else "None yet, this is your opening."
            )
        }

Agent B's last point: {last_b_point}


Give your stance for this round."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]

    response = llm_a.invoke(messages)

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
        messages.append(ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_call["id"]
        ))

        response = llm_a_base.invoke(messages)  # Final call — NO tools

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
        "agent_a_history": state["agent_a_history"] + [new_entry]
    }