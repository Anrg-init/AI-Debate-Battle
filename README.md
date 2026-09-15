# AI Debate Battle

![alt text](coverpage.png)

A Django web app that runs structured AI debates. A clarifier validates the topic, two agents argue opposing positions, a referee summarizes the arguments, and a judge selects a winner. Users can optionally upload documents for RAG-based context and view debate history.

## Stack

- Django
- LangGraph
- Google Gemini and Groq
- Tavily search
- FAISS-based document retrieval

## Flow
[text](graph2.png)

## Setup

```bash
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with the API keys used by the agents:

```env
Gemini_init_agent_a_key=...
GEMINI_API_KEY_565_agent_b=...
Gemini_Electronic_Referree_key=...
GROQ_API_KEY_electronic_clar=...
GROQ_API_KEY_init_judge=...
TAVILY_API_KEY=...
```

Run the application:

```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/app/` and create an account to start a debate.

The main debate graph is defined in `graph.py`; AI nodes are in `nodes/`, and document retrieval is implemented in `rag/`.
