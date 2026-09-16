let isUploading = false;
let hasDocuments = false;
let currentThreadId = crypto.randomUUID();
let activeSource = null;
let debateCompleted = false;

const statusPill = document.getElementById("status-pill");
const statusText = document.getElementById("status-text");
const inputStatus = document.getElementById("input-status");
const chatArea = document.getElementById("chat-area");
const topicInput = document.querySelector('input[name="topic"]');
const historyList = document.getElementById("history-list");
const sidebar = document.getElementById("debate-sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebarClose = document.getElementById("sidebar-close");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");

function setSidebarOpen(isOpen) {
    sidebar.classList.toggle("is-open", isOpen);
    sidebarBackdrop.classList.toggle("is-visible", isOpen);
    sidebarToggle.setAttribute("aria-expanded", String(isOpen));
}

function setStatus(message, state = "idle") {
    statusText.textContent = message;
    statusPill.dataset.state = state;
}

function setInputStatus(message, state = "") {
    inputStatus.textContent = message;
    inputStatus.dataset.state = state;
}

function setChatLoader(message) {
    const existingLoader = document.getElementById("chat-loader");

    if (!message) {
        existingLoader?.remove();
        return;
    }

    if (existingLoader) {
        existingLoader.querySelector(".loader-text").textContent = message;
        return;
    }

    const loader = document.createElement("div");
    loader.id = "chat-loader";
    loader.className = "message assistant chat-loader";
    loader.innerHTML = '<span class="loading-dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="loader-text"></span>';
    loader.querySelector(".loader-text").textContent = message;
    chatArea.appendChild(loader);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function setHistoryLoader(isLoading) {
    if (isLoading) {
        historyList.innerHTML = '<div class="history-loading"><span class="spinner" aria-hidden="true"></span><span>Loading debates...</span></div>';
    }
}

function renderSources(container, sources) {
    if (!Array.isArray(sources) || sources.length === 0) {
        return;
    }

    const sourceList = document.createElement("div");
    sourceList.className = "message-sources";

    const sourceHeading = document.createElement("span");
    sourceHeading.className = "sources-heading";
    sourceHeading.textContent = "SOURCES";
    sourceList.appendChild(sourceHeading);

    sources.forEach((source, index) => {
        if (!source || !source.url) {
            return;
        }

        const link = document.createElement("a");
        link.className = "source-link";
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = source.title || `Source ${index + 1}`;
        sourceList.appendChild(link);
    });

    if (sourceList.querySelector(".source-link")) {
        container.appendChild(sourceList);
    }
}

function revealText(element, text) {
    const value = text || "No information available.";
    let position = 0;
    const tokenSize = 3;

    element.textContent = "";

    function revealNextToken() {
        position = Math.min(position + tokenSize, value.length);
        element.textContent = value.slice(0, position);
        if (position < value.length) {
            window.setTimeout(revealNextToken, 18);
        }
    }

    revealNextToken();
}

function createAgentMessage(entry, speaker) {
    const isAgentA = speaker === "agent_a";
    const message = document.createElement("div");
    const displayRound = Number(entry.round || 0) + 1;
    message.className = isAgentA ? "message agent-a" : "message agent-b";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = `${isAgentA ? "AGENT GREY" : "AGENT NAVY"} · ROUND ${displayRound}`;

    const argument = document.createElement("p");
    argument.className = "message-text";
    revealText(argument, entry.argument || "No argument was returned.");

    message.append(label, argument);
    renderSources(message, entry.sources);
    return message;
}

function appendRoundDivider(round) {
    const divider = document.createElement("div");
    divider.className = "round-divider";
    divider.innerHTML = `<span>ROUND ${Number(round || 0) + 1}</span>`;
    chatArea.appendChild(divider);
}

function createResultSection(title, content, className = "") {
    const section = document.createElement("section");
    section.className = `result-section ${className}`.trim();

    const heading = document.createElement("h3");
    heading.textContent = title;

    const body = document.createElement("p");
    revealText(body, content);

    section.append(heading, body);
    return section;
}

function createRefereeCard(data) {
    const card = document.createElement("article");
    card.className = "message result-card referee-card";

    const header = document.createElement("div");
    header.className = "result-header";
    header.innerHTML = '<span class="result-icon">R</span><div><div class="message-label">REFEREE</div><p class="result-subtitle">Neutral analysis of both cases</p></div>';

    const sections = document.createElement("div");
    sections.className = "result-sections referee-sections";
    sections.append(
        createResultSection("AGENT GREY · CASE SUMMARY", data.agent_a_summary, "agent-a-summary"),
        createResultSection("AGENT NAVY · CASE SUMMARY", data.agent_b_summary, "agent-b-summary")
    );

    card.append(header, sections);
    return card;
}

function createJudgeCard(decision) {
    const card = document.createElement("article");
    card.className = "message result-card judge-card";

    const header = document.createElement("div");
    header.className = "result-header";
    header.innerHTML = '<span class="result-icon">J</span><div><div class="message-label">JUDGE DECISION</div><p class="result-subtitle">Final evaluation</p></div>';

    const verdict = document.createElement("div");
    verdict.className = "verdict-row";
    verdict.innerHTML = '<span class="verdict-label">WINNER</span><strong></strong>';
    verdict.querySelector("strong").textContent = decision.winner || "Undetermined";

    const sections = document.createElement("div");
    sections.className = "result-sections judge-sections";
    sections.append(
        createResultSection("REASONING", decision.reasoning),
        createResultSection("FINAL ANSWER", decision.final_answer, "final-answer")
    );

    card.append(header, verdict, sections);
    return card;
}

function setEmptyState(isVisible) {
    const emptyState = document.getElementById("empty-state");
    if (emptyState) {
        emptyState.hidden = !isVisible;
    }
}

function renderEmptyState() {
    chatArea.innerHTML = `
        <div class="empty-state" id="empty-state">
            <div class="empty-state-mark">⚖</div>
            <h2>Enter your topic</h2>
            <p>Let the agents debate before you decide.</p>
        </div>
    `;
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function updateButtonState() {
    const topic = document.querySelector('input[name="topic"]').value.trim();
    const submitButton = document.querySelector('button[type="submit"]');

    if (isUploading || activeSource) {
        submitButton.disabled = true;
    } else if (topic.length > 0) {
        submitButton.disabled = false;
    } else {
        submitButton.disabled = true;
    }
}

topicInput.addEventListener("input", () => {
    setEmptyState(topicInput.value.trim().length === 0 && !activeSource);
    updateButtonState();
});

document.querySelector('input[name="document"]').addEventListener("change", async function() {
    const file = this.files[0];
    if (!file) return;

    isUploading = true;
    setInputStatus("Uploading and indexing document...", "loading");
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
            setInputStatus("Document ready for this debate.", "success");
        }
    } catch (error) {
        console.error("Upload failed:", error);
        setInputStatus("Document upload failed. Please try again.", "error");
    } finally {
        isUploading = false;
        updateButtonState();
    }
});

document.getElementById("new-chat-btn").addEventListener("click", () => {
    currentThreadId = crypto.randomUUID();
    hasDocuments = false;
    renderEmptyState();
    topicInput.value = "";
    document.querySelector('input[name="document"]').value = "";
    updateButtonState();
    setSidebarOpen(false);
});

sidebarToggle.addEventListener("click", () => setSidebarOpen(true));
sidebarClose.addEventListener("click", () => setSidebarOpen(false));
sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));





document.getElementById("debate-form").addEventListener("submit", (event) => {
    event.preventDefault();

    if (activeSource) {
        return;
    }

    const topic = topicInput.value.trim();
    topicInput.value = "";
    setEmptyState(false);
    debateCompleted = false;
    setStatus("Connecting to debate...", "loading");
    setInputStatus("The debate is in progress.", "loading");
    setChatLoader("Starting the debate...");
    updateButtonState();

    activeSource = new EventSource(
        "stream/?topic=" + encodeURIComponent(topic) +
        "&has_documents=" + hasDocuments +
        "&thread_id=" + currentThreadId
    );


    let lastRenderedRound = null;

    activeSource.onmessage = (event) => {
        setChatLoader(null);
        const ai_output = JSON.parse(event.data);
        const nodeName = Object.keys(ai_output)[0];
        const nodeData = ai_output[nodeName];

        if (nodeName === "clarifier") {
            if (!nodeData.is_valid) {
                const div = document.createElement("div");
                div.className = "message assistant";
                div.textContent = "That doesn't look like a valid debate topic. Could you try rephrasing it?";
                chatArea.appendChild(div);
                debateCompleted = true;
                setStatus("Topic needs clarification", "idle");
                setInputStatus("Try a more specific topic.");
            } else {
                setStatus("Agents are preparing arguments...", "loading");
                setChatLoader("Preparing the first arguments...");
            }
            return;
        }

        if (nodeName === "agent_a" || nodeName === "agent_b") {
            const historyKey = nodeName === "agent_a" ? "agent_a_history" : "agent_b_history";
            const lastEntry = nodeData[historyKey][nodeData[historyKey].length - 1];
            if (lastEntry.round !== lastRenderedRound) {
                lastRenderedRound = lastEntry.round;
                  appendRoundDivider(lastEntry.round);
            }

              chatArea.appendChild(createAgentMessage(lastEntry, nodeName));
            setStatus("Agent Navy is thinking...", "loading");
            setChatLoader("AGENT NAVY IS THINKING");
        } else if (nodeName === "agent_referre") {
              chatArea.appendChild(createRefereeCard(nodeData));
            setStatus("Judge is reviewing the debate...", "loading");
            setChatLoader("JUDGE IS REVIEWING THE ARGUMENTS");
        } else if (nodeName === "agent_judge") {
              chatArea.appendChild(createJudgeCard(nodeData.judge_final_decision));
            debateCompleted = true;
            setStatus("Debate complete", "success");
            setInputStatus("Your debate is ready to review.", "success");
        }
    };


    activeSource.onerror = () => {
        activeSource.close();
        activeSource = null;
        setChatLoader(null);
        if (!debateCompleted) {
            setStatus("Debate could not finish", "error");
            setInputStatus("The debate stopped before completion. Please try again.", "error");
        }
        updateButtonState();
        loadHistory();
    };
});




async function loadHistory() {
    setHistoryLoader(true);
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
        document.getElementById("history-count").textContent = data.debates.length;
    } catch (error) {
        console.error("Failed to load history:", error);
        historyList.innerHTML = '<div class="history-empty">Unable to load debates.</div>';
    }
}



async function loadDebate(threadId) {
    setStatus("Loading saved debate...", "loading");
    setChatLoader("Loading debate history...");
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

        let lastHistoryRound = null;
        let hasDebateContent = false;
        transcript.forEach((entry) => {
            hasDebateContent = true;
            if (entry.round !== lastHistoryRound) {
                lastHistoryRound = entry.round;
                appendRoundDivider(entry.round);
            }
            chatArea.appendChild(createAgentMessage(entry, entry.speaker));
        });

        if (result.agent_a_summary) {
            hasDebateContent = true;
              chatArea.appendChild(createRefereeCard({
                  agent_a_summary: result.agent_a_summary,
                  agent_b_summary: result.agent_b_summary
              }));
        }

        if (result.judge_final_decision && result.judge_final_decision.winner) {
            hasDebateContent = true;
              chatArea.appendChild(createJudgeCard(result.judge_final_decision));
        }
        if (!hasDebateContent) {
            renderEmptyState();
        }
        setStatus("Saved debate", "idle");
        setChatLoader(null);
    } catch (error) {
        console.error("Failed to load debate:", error);
        setStatus("Unable to load debate", "error");
        setChatLoader(null);
    }
}

renderEmptyState();
loadHistory();