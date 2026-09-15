import os
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

from graph import app as debate_graph
from rag.ingest import load_document, chunk_document, build_vector_store
from rag.store import set_vector_store
from django.http import StreamingHttpResponse, JsonResponse
import json
import uuid
from .history_store import add_debate, get_debates_for_user
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .forms import CleanSignupForm


@login_required
def home(request):
    return render(request, "Debate_app/home.html")



@login_required
def stream_debate(request):

    topic = request.GET.get("topic","")

    has_documents = request.GET.get("has_documents", "false") == "true"

    initial_state = {
            "user_input": topic,
            "input_type": "",
            "is_valid": False,
            "clarifier_attempts": 0,
            "agent_a_history": [],
            "agent_b_history": [],
            "current_round": 0,
            "agent_a_summary": "",
            "agent_b_summary": "",
            "judge_final_decision": {},
            "has_documents": has_documents,
            "retrieved_context": ""
        }


    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": thread_id}
    }

    add_debate(thread_id, request.user.id, topic)

    def event_generator():
        for chunk in debate_graph.stream(initial_state, config, stream_mode="updates"):
            yield f"data: {json.dumps(chunk)}\n\n"


    return StreamingHttpResponse(event_generator(), content_type="text/event-stream")



@login_required
def upload_document(request):
    uploaded_file = request.FILES.get('document')

    temp_path = os.path.join(settings.BASE_DIR, "temp_uploads", uploaded_file.name)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    with open(temp_path, "wb+") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    documents = load_document(temp_path)
    chunks = chunk_document(documents)
    vector_store = build_vector_store(chunks)
    set_vector_store(vector_store)

    os.remove(temp_path)  # cleanup, jaisa pehle bhi karte the

    return JsonResponse({"status": "done"})


            

def signup_view(request):
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
    logout(request)
    return redirect("home")





@login_required
def history_view(request):
    debates = get_debates_for_user(request.user.id)
    return render(request, "Debate_app/history.html", {"debates": debates})




@login_required
def history_detail_view(request, thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = debate_graph.get_state(config)

    if not state_snapshot.values:
        raise Http404("Debate not found")

    result = state_snapshot.values

    transcript = []
    for a_entry, b_entry in zip(result.get("agent_a_history", []), result.get("agent_b_history", [])):
        transcript.append({"speaker": "Agent A", "round": a_entry["round"], "argument": a_entry["argument"]})
        transcript.append({"speaker": "Agent B", "round": b_entry["round"], "argument": b_entry["argument"]})

    return render(request, "Debate_app/history_detail.html", {"result": result, "transcript": transcript})