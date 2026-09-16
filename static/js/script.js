let isUploading = false;
let hasDocuments = false;
let currentThreadId = crypto.randomUUID();
let activeSource = null;

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function updateButtonState() {
    const topic = document.querySelector('input[name="topic"]').value.trim();
    const submitButton = document.querySelector('button[type="submit"]');

    if (isUploading) {
        submitButton.disabled = true;
    } else if (topic.length > 0) {
        submitButton.disabled = false;
    } else {
        submitButton.disabled = true;
    }
}

document.querySelector('input[name="topic"]').addEventListener("input", updateButtonState);

document.querySelector('input[name="document"]').addEventListener("change", async function() {
    const file = this.files[0];
    if (!file) return;

    isUploading = true;
    updateButtonState();

    const formData = new FormData();
    formData.append("document", file);

    try {
        const response = await fetch("upload/", {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken() },
            body: formData
        });
        const data = await response.json();
        if (data.status === "done") {
            hasDocuments = true;
        }
    } catch (error) {
        console.error("Upload failed:", error);
    }

    isUploading = false;
    updateButtonState();
});

document.getElementById("new-chat-btn").addEventListener("click", () => {
    currentThreadId = crypto.randomUUID();
    hasDocuments = false;
    document.getElementById("chat-area").innerHTML = "";
    document.querySelector('input[name="topic"]').value = "";
    document.querySelector('input[name="document"]').value = "";
    updateButtonState();
});





document.getElementById("debate-form").addEventListener("submit", (event) => {
    event.preventDefault();

    if (activeSource) {
        return;
    }

    const topic = document.querySelector('input[name="topic"]').value;
    const chatArea = document.getElementById("chat-area");

    activeSource = new EventSource(
        "stream/?topic=" + encodeURIComponent(topic) +
        "&has_documents=" + hasDocuments +
        "&thread_id=" + currentThreadId
    );


    let lastRenderedRound = null;

    activeSource.onmessage = (event) => {
        const ai_output = JSON.parse(event.data);
        const nodeName = Object.keys(ai_output)[0];
        const nodeData = ai_output[nodeName];

        if (nodeName === "clarifier") {
            if (!nodeData.is_valid) {
                const div = document.createElement("div");
                div.className = "message assistant";
                div.textContent = "That doesn't look like a valid debate topic. Could you try rephrasing it?";
                chatArea.appendChild(div);
            }
            return;
        }

        if (nodeName === "agent_a" || nodeName === "agent_b") {
            const historyKey = nodeName === "agent_a" ? "agent_a_history" : "agent_b_history";
            const lastEntry = nodeData[historyKey][nodeData[historyKey].length - 1];
            const agentLabel = nodeName === "agent_a" ? "AGENT GREY" : "AGENT NAVY";
            const cssClass = nodeName === "agent_a" ? "message agent-a" : "message agent-b";

            if (lastEntry.round !== lastRenderedRound) {
                lastRenderedRound = lastEntry.round;
                const divider = document.createElement("div");
                divider.className = "round-divider";
                divider.innerHTML = `<span>ROUND ${lastEntry.round}</span>`;
                chatArea.appendChild(divider);
            }

            const div = document.createElement("div");
            div.className = cssClass;
            div.innerHTML = `
                <div class="message-label">${agentLabel} · ROUND ${lastEntry.round}</div>
                <p class="message-text"></p>
            `;
            div.querySelector(".message-text").textContent = lastEntry.argument;
            chatArea.appendChild(div);
        } else if (nodeName === "agent_referre") {
            const div = document.createElement("div");
            div.className = "message assistant";
            div.innerHTML = `
                <div class="message-label">REFEREE SUMMARY</div>
                <p class="message-text"></p>
            `;
            div.querySelector(".message-text").textContent = `A: ${nodeData.agent_a_summary} | B: ${nodeData.agent_b_summary}`;
            chatArea.appendChild(div);
        } else if (nodeName === "agent_judge") {
            const div = document.createElement("div");
            div.className = "message assistant";
            div.innerHTML = `
                <div class="message-label">JUDGE DECISION — ${nodeData.judge_final_decision.winner}</div>
                <p class="message-text"></p>
            `;
            div.querySelector(".message-text").textContent = nodeData.judge_final_decision.reasoning;
            chatArea.appendChild(div);
        }
    };


    activeSource.onerror = () => {
        activeSource.close();
        activeSource = null;
        loadHistory();
    };
});




async function loadHistory() {
    try {
        const response = await fetch("history-data/");
        const data = await response.json();

        const historyList = document.getElementById("history-list");
        historyList.innerHTML = "";

        data.debates.forEach((debate) => {
            const item = document.createElement("div");
            item.className = debate.thread_id === currentThreadId ? "history-item active" : "history-item";
            item.textContent = debate.topic;
            item.addEventListener("click", () => loadDebate(debate.thread_id));
            historyList.appendChild(item);
        });
    } catch (error) {
        console.error("Failed to load history:", error);
    }
}



async function loadDebate(threadId) {
    try {
        const response = await fetch(`history/${threadId}/`);
        const result = await response.json();

        currentThreadId = threadId;
        hasDocuments = result.has_documents || false;

        const chatArea = document.getElementById("chat-area");
        chatArea.innerHTML = "";

        const transcript = [];
        for (let i = 0; i < result.agent_a_history.length; i++) {
            transcript.push({ speaker: "agent_a", ...result.agent_a_history[i] });
            transcript.push({ speaker: "agent_b", ...result.agent_b_history[i] });
        }

        transcript.forEach((entry) => {
            const div = document.createElement("div");
            div.className = entry.speaker === "agent_a" ? "message agent-a" : "message agent-b";
            div.textContent = `${entry.speaker} (Round ${entry.round}): ${entry.argument}`;
            chatArea.appendChild(div);
        });

        if (result.agent_a_summary) {
            const div = document.createElement("div");
            div.className = "message assistant";
            div.textContent = `Referee Summary — A: ${result.agent_a_summary} | B: ${result.agent_b_summary}`;
            chatArea.appendChild(div);
        }

        if (result.judge_final_decision && result.judge_final_decision.winner) {
            const div = document.createElement("div");
            div.className = "message assistant";
            div.textContent = `Judge Decision — Winner: ${result.judge_final_decision.winner} | ${result.judge_final_decision.reasoning}`;
            chatArea.appendChild(div);
        }
    } catch (error) {
        console.error("Failed to load debate:", error);
    }
}

loadHistory();