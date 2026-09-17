import os
import json
import uuid
# JsonResponse is used by normal AJAX endpoints; StreamingHttpResponse keeps
# the debate connection open while LangGraph emits completed node updates.
from django.http import JsonResponse, StreamingHttpResponse, Http404
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

# This is the compiled LangGraph workflow. The frontend never calls graph.py
# directly; it reaches this object through the stream_debate view below.
from graph import app as debate_graph
from nodes.clar import clarifier_node
from rag.ingest import load_document, chunk_document, build_vector_store
from rag.store import set_vector_store, get_vector_store
from .forms import CleanSignupForm
from .models import Debate


def landing(request):
    """Render the public product landing page before users enter the workspace."""
    return render(request, "Debate_app/landing.html")


@login_required
def home(request):
    """Render the debate shell; script.js fills and updates it in the browser."""
    return render(request, "Debate_app/home.html")


@login_required
def stream_debate(request):
    """Start one debate and expose its LangGraph node updates as SSE events.

    Connection: script.js opens the generated stream endpoint -> this view builds
    the initial state -> LangGraph runs clarifier/agents/referee/judge -> each
    completed node is yielded to the browser as a `data:` Server-Sent Event.
    This is node-level streaming, not provider token-by-token streaming.
    """
    # Values arrive from the query string assembled in script.js.
    topic = request.GET.get("topic", "")
    has_documents = request.GET.get("has_documents", "false") == "true"
    thread_id = request.GET.get("thread_id") or str(uuid.uuid4())
    try:
        rounds = int(request.GET.get("rounds", "2"))
    except (TypeError, ValueError):
        rounds = 2
    if rounds not in {1, 2, 3}:
        rounds = 2

    # LangGraph uses this dictionary as the starting DebateState for this
    # thread. Empty histories are populated as the graph visits each node.
    initial_state = {
        "user_input": topic,
        "input_type": "",
        "is_valid": False,
        "clarifier_attempts": 0,
        "agent_a_history": [],
        "agent_b_history": [],
        "current_round": 0,
        "rounds": rounds,
        "agent_a_summary": "",
        "agent_b_summary": "",
        "judge_final_decision": {},
        "has_documents": has_documents,
        "retrieved_context": ""
    }

    clarification = clarifier_node(initial_state)
    initial_state.update(clarification)

    if not initial_state["is_valid"]:
        def invalid_event_generator():
            yield f"data: {json.dumps({'clarifier': clarification})}\n\n"

        return StreamingHttpResponse(
            invalid_event_generator(),
            content_type="text/event-stream"
        )

    # The thread ID lets LangGraph's checkpointer associate this run with the
    # same debate when history_detail_view later reads it.
    config = {"configurable": {"thread_id": thread_id}}

    # Django stores ownership/topic metadata. The actual graph state is stored
    # by LangGraph's configured checkpointer, not in this Debate row.
    debate, created = Debate.objects.get_or_create(
        thread_id=thread_id,
        defaults={"user": request.user, "topic": topic},
    )
    if not created and debate.user_id != request.user.id:
        return JsonResponse({"error": "Invalid thread_id"}, status=409)

    def event_generator():
        """Convert LangGraph updates into browser-readable SSE messages."""
        try:
            for chunk in debate_graph.stream(initial_state, config, stream_mode="updates"):
                # SSE messages end with two newlines. json.dumps preserves nested
                # agent histories, sources, referee data, and judge data.
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({'stream_complete': True})}\n\n"
        except Exception as exc:
            print(f"[stream_debate] Graph execution failed: {exc}")
            yield f"data: {json.dumps({'error': 'The debate could not be completed.', 'details': str(exc)})}\n\n"

    # Django starts iterating event_generator lazily, so the response can send
    # each update before the complete debate has finished.
    return StreamingHttpResponse(event_generator(), content_type="text/event-stream")




@login_required
def upload_document(request):
    """Receive a document, build its vector store, and return upload status.

    Connection: the file input in script.js sends FormData to `upload/` -> this
    view writes a temporary file -> RAG ingestion creates embeddings/indexes ->
    the shared store is set -> the next debate can retrieve this context.
    """
    uploaded_file = request.FILES.get('document')
    if uploaded_file is None:
        return JsonResponse({"error": "No document was provided."}, status=400)

    temp_dir = os.path.join(settings.BASE_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}{file_extension}")

    try:
        # Django's UploadedFile.chunks() avoids loading a large file into memory.
        with open(temp_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # These functions parse the file, split it, and build searchable vectors.
        documents = load_document(temp_path)
        chunks = chunk_document(documents)
        vector_store = build_vector_store(chunks)
        set_vector_store(vector_store)
    except Exception:
        return JsonResponse({"error": "The document could not be processed."}, status=500)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return JsonResponse({"status": "done"})


def signup_view(request):
    """Validate a new account, log it in, and redirect to the debate home."""
    if request.method == "POST":
        form = CleanSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = CleanSignupForm()

    return render(request, "Debate_app/signup.html", {"form": form})


def login_view(request):
    """Validate credentials and redirect successful users to the debate home."""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "Debate_app/login.html", {"form": form})


def logout_view(request):
    """Clear the Django session and return the user to the public landing page."""
    logout(request)
    return redirect("landing")


@login_required
def history_json(request):
    """Return the current user's debate list for the sidebar fetch in script.js."""
    debates = Debate.objects.filter(user=request.user).order_by('-created_at')
    data = [{"thread_id": d.thread_id, "topic": d.topic} for d in debates]
    return JsonResponse({"debates": data})


@login_required
def history_detail_view(request, thread_id):
    """Return one saved LangGraph state for the selected sidebar debate.

    script.js uses this JSON to rebuild agent messages, sources, referee cards,
    and the judge card without loading a separate page.
    """
    if not Debate.objects.filter(thread_id=thread_id, user=request.user).exists():
        return JsonResponse({"error": "not found"}, status=404)

    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = debate_graph.get_state(config)
    except Exception as exc:
        print(f"[history_detail_view] State lookup failed: {exc}")
        return JsonResponse({"error": "Unable to load debate history."}, status=500)

    if not state_snapshot.values:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse(state_snapshot.values)