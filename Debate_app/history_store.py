debate_history = []


def add_debate(thread_id, user_id, topic):
    debate_history.append({
        "thread_id": thread_id,
        "user_id": user_id,
        "topic": topic
    })


def get_debates_for_user(user_id):
    return [d for d in debate_history if d["user_id"] == user_id]