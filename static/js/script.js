// These variables are the browser-side state for one open debate session.
// They coordinate the template controls with the Django endpoints and SSE.
let isUploading = false;
let hasDocuments = false;
let currentThreadId = crypto.randomUUID();
let activeSource = null;
let debateCompleted = false;

// These selectors are the connection points to IDs in templates/base2.html.
// If an ID changes in the template, the related browser behavior also breaks.
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
const roundsSelect = document.getElementById("rounds-select");

function setSidebarOpen(isOpen) {
    // Mobile sidebar state is represented by CSS classes; no page navigation
    // occurs when the history drawer opens or closes.
    sidebar.classList.toggle("is-open", isOpen);
    sidebarBackdrop.classList.toggle("is-visible", isOpen);
    sidebarToggle.setAttribute("aria-expanded", String(isOpen));
}

function setStatus(message, state = "idle") {
    // Updates the top-bar text and data-state, which CSS uses for dot colors.
    statusText.textContent = message;
    statusPill.dataset.state = state;
}

function setInputStatus(message, state = "") {
    // Updates the small status line below the composer for upload/debate state.
    inputStatus.textContent = message;
    inputStatus.dataset.state = state;
}

function showDebateError(message) {
    const errorMessage = document.createElement("div");
    errorMessage.className = "message assistant error-message";
    errorMessage.textContent = `Error: ${message}`;
    chatArea.appendChild(errorMessage);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function setChatLoader(message) {
    // Adds or updates one loader message while the next LangGraph node is busy.
    // The loader is removed as soon as an SSE event arrives.
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
    // Gives the sidebar immediate feedback while history-data/ is being fetched.
    if (isLoading) {
        historyList.innerHTML = '<div class="history-loading"><span class="spinner" aria-hidden="true"></span><span>Loading debates...</span></div>';
    }
}

function renderSources(container, sources) {
    // Agent nodes attach [{title, url}] source objects to each history entry.
    // This function converts only valid URLs into safe, clickable source links.
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
    // This is a visual typewriter effect applied after a complete node update.
    // It is not provider token streaming; the full text already arrived here.
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
    // Build one Agent Grey/Navy message card from a graph history entry.
    // Backend rounds start at 0, so the UI adds 1 for human-facing labels.
    const isAgentA = speaker === "agent_a";
    const message = document.createElement("div");
    const displayRound = Number(entry.round || 0) + 1;
    message.className = isAgentA ? "message agent-a" : "message agent-b";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = `${isAgentA ? "AGENT TOM" : "AGENT JERRY"} · ROUND ${displayRound}`;

    const argument = document.createElement("p");
    argument.className = "message-text";
    revealText(argument, entry.argument || "No argument was returned.");

    message.append(label, argument);
    renderSources(message, entry.sources);
    return message;
}

function appendRoundDivider(round) {
    // Keeps the transcript grouped by debate round as agent cards are appended.
    const divider = document.createElement("div");
    divider.className = "round-divider";
    divider.innerHTML = `<span>ROUND ${Number(round || 0) + 1}</span>`;
    chatArea.appendChild(divider);
}

function createResultSection(title, content, className = "") {
    // Shared section builder for the structured referee and judge cards.
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
    // Referee data arrives after both agents finish; render the two cases as
    // separate sections instead of flattening them into one paragraph.
    const card = document.createElement("article");
    card.className = "message result-card referee-card";

    const header = document.createElement("div");
    header.className = "result-header";
    header.innerHTML = '<span class="result-icon">R</span><div><div class="message-label">THE REFEREE</div><p class="result-subtitle">Neutral analysis of both cases</p></div>';

    const sections = document.createElement("div");
    sections.className = "result-sections referee-sections";
    sections.append(
        createResultSection("AGENT TOM · CASE SUMMARY", data.agent_a_summary, "agent-a-summary"),
        createResultSection("AGENT JERRY · CASE SUMMARY", data.agent_b_summary, "agent-b-summary")
    );

    card.append(header, sections);
    return card;
}

function createJudgeCard(decision) {
    // Judge data contains winner, reasoning, and final_answer. Each gets a
    // separate visual section so the final result is easy to scan.
    const card = document.createElement("article");
    card.className = "message result-card judge-card";

    const header = document.createElement("div");
    header.className = "result-header";
    header.innerHTML = '<span class="result-icon">J</span><div><div class="message-label">THE JUDGE</div><p class="result-subtitle">Final evaluation</p></div>';

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
    // Hide/show the prompt already present in the chat-area template.
    const emptyState = document.getElementById("empty-state");
    if (emptyState) {
        emptyState.hidden = !isVisible;
    }
}

function renderEmptyState() {
    // Rebuild the centered new-chat prompt after clearing the transcript.
    chatArea.innerHTML = `
        <div class="empty-state" id="empty-state">
            <div class="empty-state-mark">⚖</div>
            <h2>Set the question</h2>
            <p>Two agents will test both sides before the verdict.</p>
        </div>
    `;
}

function getCsrfToken() {
    // Django renders this hidden token in the debate form; upload uses it for
    // CSRF protection because upload_document is a POST endpoint.
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function updateButtonState() {
    // The submit button is enabled only when there is a topic and no request or
    // upload is currently active.
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

// Typing hides the empty prompt; clearing the input restores it when no debate
// stream is active. This is why the prompt reacts immediately to user input.
topicInput.addEventListener("input", () => {
    setEmptyState(topicInput.value.trim().length === 0 && !activeSource);
    updateButtonState();
});

// File selection starts an AJAX upload. The server performs RAG indexing before
// returning {status: "done"}; only then can the next debate use the document.
document.querySelector('input[name="document"]').addEventListener("change", async function() {
    const file = this.files[0];
    if (!file) return;

    isUploading = true;
    setInputStatus("Uploading and indexing document...", "loading");
    updateButtonState();

    const formData = new FormData();
    formData.append("document", file);

    try {
        const response = await fetch(window.debateUrls.upload, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken() },
            body: formData
        });
        if (!response.ok) {
            throw new Error(`Upload failed with status ${response.status}`);
        }
        const data = await response.json();
        if (data.status === "done") {
            hasDocuments = true;
            setInputStatus("Document ready for this debate.", "success");
        } else {
            throw new Error(data.error || "Document processing failed");
        }
    } catch (error) {
        console.error("Upload failed:", error);
        setInputStatus("Document upload failed. Please try again.", "error");
    } finally {
        isUploading = false;
        updateButtonState();
    }
});

// New debate resets client state and replaces the transcript with the prompt.
document.getElementById("new-chat-btn").addEventListener("click", () => {
    currentThreadId = crypto.randomUUID();
    hasDocuments = false;
    renderEmptyState();
    topicInput.value = "";
    document.querySelector('input[name="document"]').value = "";
    updateButtonState();
    setSidebarOpen(false);
});

// These three listeners control the mobile history drawer.
sidebarToggle.addEventListener("click", () => setSidebarOpen(true));
sidebarClose.addEventListener("click", () => setSidebarOpen(false));
sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));





// Main connection flow:
// form submit -> EventSource opens stream/ -> views.py yields SSE updates ->
// onmessage identifies the graph node -> the matching card is appended here.
document.getElementById("debate-form").addEventListener("submit", (event) => {
    event.preventDefault();

    if (activeSource) {
        return;
    }

    const topic = topicInput.value.trim();
    setEmptyState(false);
    debateCompleted = false;
    setStatus("Connecting to debate...", "loading");
    setInputStatus("The debate is in progress.", "loading");
    setChatLoader("Starting the debate...");
    updateButtonState();

    const streamUrl = new URL(window.debateUrls.stream, window.location.origin);
    streamUrl.searchParams.set("topic", topic);
    streamUrl.searchParams.set("has_documents", hasDocuments);
    streamUrl.searchParams.set("rounds", roundsSelect.value);
    streamUrl.searchParams.set("thread_id", currentThreadId);
    activeSource = new EventSource(streamUrl);


    let lastRenderedRound = null;

    // Each event is one completed LangGraph node update, not one model token.
    activeSource.onmessage = (event) => {
        try {
            setChatLoader(null);
            const ai_output = JSON.parse(event.data);
            const nodeName = Object.keys(ai_output)[0];
            const nodeData = ai_output[nodeName];
            if (!nodeName || !nodeData) {
                throw new Error("The debate returned an empty update");
            }

            if (nodeName === "error") {
                showDebateError(nodeData.details || nodeData.error || "The debate could not be completed.");
                debateCompleted = true;
                setStatus("Debate stopped", "error");
                setInputStatus("The debate stopped because of an error. You can start a new debate.", "error");
                activeSource?.close();
                activeSource = null;
                currentThreadId = crypto.randomUUID();
                updateButtonState();
                loadHistory();
                return;
            }

            if (nodeName === "stream_complete") {
                debateCompleted = true;
                activeSource?.close();
                activeSource = null;
                updateButtonState();
                loadHistory();
                return;
            }

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
                const history = nodeData[historyKey];
                const lastEntry = Array.isArray(history) ? history[history.length - 1] : null;
                if (!lastEntry) {
                    throw new Error("The debate returned an incomplete agent update");
                }
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
        } catch (error) {
            console.error("Invalid debate update:", error);
            showDebateError(error.message || "The debate returned an invalid update.");
            activeSource?.close();
            activeSource = null;
            currentThreadId = crypto.randomUUID();
            setChatLoader(null);
            setStatus("Debate could not finish", "error");
            setInputStatus("The debate returned an invalid update. Please try again.", "error");
            updateButtonState();
        }
    };


    // EventSource reports normal stream closure and real failures through this
    // callback, so the UI closes the connection and refreshes history.
    activeSource.onerror = () => {
        activeSource?.close();
        activeSource = null;
        setChatLoader(null);
        if (!debateCompleted) {
            setStatus("Debate could not finish", "error");
            setInputStatus("The debate stopped before completion. Please try again.", "error");
            currentThreadId = crypto.randomUUID();
        }
        updateButtonState();
        loadHistory();
    };
});




async function loadHistory() {
    // Fetch the lightweight sidebar list from history-data/ and attach a click
    // handler that loads the selected thread's full graph state.
    setHistoryLoader(true);
    try {
        const response = await fetch(window.debateUrls.history);
        if (!response.ok) {
            throw new Error(`History request failed with status ${response.status}`);
        }
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
    // Fetch one saved state from history/<thread_id>/ and rebuild the same cards
    // used by live streaming, including rounds, sources, referee, and judge.
    setStatus("Loading saved debate...", "loading");
    setChatLoader("Loading debate history...");
    try {
        const detailUrl = window.debateUrls.historyDetail.replace(
            "THREAD_ID_PLACEHOLDER",
            encodeURIComponent(threadId)
        );
        const response = await fetch(detailUrl);
        if (!response.ok) {
            throw new Error(`Debate history request failed with status ${response.status}`);
        }
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

// Initial page boot: show the prompt immediately, then populate sidebar history.
renderEmptyState();
loadHistory();