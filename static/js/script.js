let isUploading = false;
let hasDocuments = false;

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
        console.log("Upload response:", data);
        if (data.status === "done") {
            hasDocuments = true;
        }
    } catch (error) {
        console.error("Upload failed:", error);
    }

    isUploading = false;
    updateButtonState();
});

document.getElementById("debate-form").addEventListener("submit", (event) => {
    event.preventDefault();

    const topic = document.querySelector('input[name="topic"]').value;
    const source = new EventSource(
        "stream/?topic=" + encodeURIComponent(topic) + "&has_documents=" + hasDocuments
    );

    source.onmessage = (event) => {
        const ai_output = JSON.parse(event.data);
        const nodeName = Object.keys(ai_output)[0];
        const nodeData = ai_output[nodeName];
        console.log("Node:", nodeName, nodeData);

        let text = "";

        if (nodeName === "clarifier") {
            const message = document.getElementById("div1");
            
            if (!nodeData.is_valid) {
                message.textContent = "Please enter a correct input";
            }
            return;

        }

        if (nodeName === "agent_a" || nodeName === "agent_b") {
            const historyKey = nodeName === "agent_a" ? "agent_a_history" : "agent_b_history";
            const lastEntry = nodeData[historyKey][nodeData[historyKey].length - 1];
            text = `${nodeName} (Round ${lastEntry.round}): ${lastEntry.argument}`;
        } else if (nodeName === "agent_referre") {
            text = `Referee Summary — A: ${nodeData.agent_a_summary} | B: ${nodeData.agent_b_summary}`;
        } else if (nodeName === "agent_judge") {
            text = `Judge Decision — Winner: ${nodeData.judge_final_decision.winner} | ${nodeData.judge_final_decision.reasoning}`;
        } else {
            return;
        }

        const ai_output_div = document.createElement("div");
        ai_output_div.textContent = text;
        document.body.appendChild(ai_output_div);
    };

    source.onerror = () => {
        console.log("Stream ended or errored");
        source.close();
    };
});