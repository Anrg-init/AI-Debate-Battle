# Multi Agent Debate System

A compact LangGraph-based multi-agent debate app that validates a user prompt, runs two opposing AI agents in a small debate loop, summarizes both sides, and lets a judge decide the winner.

![alt text](coverpage.png)

## Overview

This project combines:
- LangGraph for workflow orchestration
- Groq for the clarifier and judge
- Google Gemini for the two debate agents and referee
- Tavily search for external evidence

## Flow

![alt text](image.png)

## Project structure

```text
debate_system/
├── graph.py
├── main.py
├── requirements.txt
├── .env
├── nodes/
│   ├── clar.py
│   ├── agent_a.py
│   ├── agent_b.py
│   ├── agent_referre.py
│   └── agent_judge.py
├── state/
│   └── state.py
├── tools/
│   └── tools.py
└── README.md
```

## How it works

1. The clarifier checks whether the user input is meaningful and whether it is factual or opinion-based.
2. If invalid, it asks for a retry up to a limit.
3. Agent A argues for the topic and Agent B argues against it.
4. Each agent may use Tavily search to support its argument.
5. A referee summarizes both sides.
6. A judge evaluates the summaries and produces a winner plus a final answer.

## State

The shared debate state is defined in `state/state.py` and includes:
- `user_input`
- `input_type`
- `is_valid`
- `clarifier_attempts`
- `agent_a_history`
- `agent_b_history`
- `current_round`
- `agent_a_summary`
- `agent_b_summary`
- `judge_final_decision`

## Setup

```bash
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
python main.py
```

Add your API keys in `.env` before running.

## Notes

- The current debate loop is short and fixed.
- `main.py` uses a sample input and runs the graph once.
- The project depends on external AI/search services, so API keys must be valid.

## Upcoming features

- RAG-based documentation and knowledge retrieval
- MAD (Multi-Agent Debate) enhancements with deeper reasoning and context-aware rounds
- Proper UI for real-time debate visualization and interaction
- MCP tools integration for structured tool orchestration
- Authentication, user sessions, and dashboard-based workflows
- Analytics, evaluation metrics, and debate history tracking
- Better production-ready architecture for deployment and scaling


## Summary

This is a small debate engine built with LangGraph that simulates a structured AI-vs-AI argument, summarizes both positions, and judges the outcome.
