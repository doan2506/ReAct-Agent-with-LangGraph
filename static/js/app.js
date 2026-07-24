/**
 * Client JavaScript Logic for LangGraph ReAct Loop Visualizer
 * Manages SSE Stream Connection, Dynamic Graph Node Highlighting,
 * Trajectory Cards Rendering, and Telemetry Updates.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const promptInput = document.getElementById("promptInput");
    const runBtn = document.getElementById("runBtn");
    const clearBtn = document.getElementById("clearBtn");
    const simToggle = document.getElementById("simToggle");
    const modelSelect = document.getElementById("modelSelect");
    const systemPrompt = document.getElementById("systemPrompt");

    const statusBadge = document.getElementById("statusBadge");
    const statusText = document.getElementById("statusText");

    const statSteps = document.getElementById("statSteps");
    const statToolCalls = document.getElementById("statToolCalls");
    const statElapsed = document.getElementById("statElapsed");

    const trajectoryFeed = document.getElementById("trajectoryFeed");
    const emptyState = document.getElementById("emptyState");

    // Nodes
    const nodeStart = document.getElementById("node-start");
    const nodeModel = document.getElementById("node-call_model");
    const nodeTools = document.getElementById("node-tools");
    const nodeEnd = document.getElementById("node-__end__");

    let eventSource = null;
    let stepCounter = 0;
    let toolCallCounter = 0;
    let startTime = 0;
    let timerInterval = null;

    // Fetch API status & models on load
    fetchConfig();

    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            if (data.models) {
                modelSelect.innerHTML = data.models.map(m => 
                    `<option value="${m.id}" ${m.id === data.default_model ? 'selected' : ''}>
                        ${m.name} ${m.available ? '' : '(No Key)'}
                    </option>`
                ).join('');
            }
        } catch (err) {
            console.warn("Could not fetch API config:", err);
        }
    }

    // Set Active Node in Graph Diagram
    function setActiveNode(nodeId) {
        [nodeStart, nodeModel, nodeTools, nodeEnd].forEach(node => {
            if (node) node.classList.remove("active");
        });

        const targetNode = document.getElementById(`node-${nodeId}`);
        if (targetNode) {
            targetNode.classList.add("active");
        }
    }

    // Sample Prompt Pills Handler
    document.querySelectorAll(".pill-btn").forEach(pill => {
        pill.addEventListener("click", () => {
            const prompt = pill.getAttribute("data-prompt");
            promptInput.value = prompt;
            startReActLoop();
        });
    });

    // Clear Stream Button
    clearBtn.addEventListener("click", resetStreamView);

    function resetStreamView() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        clearInterval(timerInterval);
        trajectoryFeed.innerHTML = "";
        trajectoryFeed.appendChild(emptyState);
        emptyState.style.display = "flex";

        stepCounter = 0;
        toolCallCounter = 0;
        statSteps.textContent = "0";
        statToolCalls.textContent = "0";
        statElapsed.textContent = "0.0s";

        setActiveNode("start");
        updateStatus("System Ready", "idle");
    }

    function updateStatus(text, state) {
        statusText.textContent = text;
        statusBadge.className = `status-badge ${state}`;
    }

    // Run Button Click Handler
    runBtn.addEventListener("click", startReActLoop);

    function startReActLoop() {
        const query = promptInput.value.trim();
        if (!query) return;

        resetStreamView();
        emptyState.style.display = "none";

        updateStatus("Executing ReAct Loop...", "running");
        setActiveNode("call_model");

        startTime = Date.now();
        timerInterval = setInterval(() => {
            const sec = ((Date.now() - startTime) / 1000).toFixed(1);
            statElapsed.textContent = `${sec}s`;
        }, 100);

        const params = new URLSearchParams({
            query: query,
            model: modelSelect.value,
            system_prompt: systemPrompt.value,
            simulation: simToggle.checked ? "true" : "false"
        });

        eventSource = new EventSource(`/api/stream?${params.toString()}`);

        eventSource.addEventListener("start", (e) => {
            const data = JSON.parse(e.data);
            appendStartCard(data);
        });

        eventSource.addEventListener("node_change", (e) => {
            const data = JSON.parse(e.data);
            setActiveNode(data.node);
            if (data.step) {
                stepCounter = data.step;
                statSteps.textContent = stepCounter;
            }
        });

        eventSource.addEventListener("reasoning", (e) => {
            const data = JSON.parse(e.data);
            appendReasoningCard(data);
        });

        eventSource.addEventListener("tool_call", (e) => {
            const data = JSON.parse(e.data);
            toolCallCounter++;
            statToolCalls.textContent = toolCallCounter;
            appendToolCallCard(data);
        });

        eventSource.addEventListener("tool_result", (e) => {
            const data = JSON.parse(e.data);
            appendToolResultCard(data);
        });

        eventSource.addEventListener("final_answer", (e) => {
            const data = JSON.parse(e.data);
            appendFinalAnswerCard(data);
        });

        eventSource.addEventListener("complete", (e) => {
            const data = JSON.parse(e.data);
            clearInterval(timerInterval);
            setActiveNode("__end__");
            updateStatus("Loop Completed", "completed");
            eventSource.close();
        });

        eventSource.addEventListener("error", (e) => {
            clearInterval(timerInterval);
            let errMsg = "An error occurred during execution.";
            try {
                if (e.data) errMsg = JSON.parse(e.data).error || errMsg;
            } catch (err) {}
            appendErrorCard(errMsg);
            updateStatus("Error Encountered", "idle");
            if (eventSource) eventSource.close();
        });
    }

    // Render Trajectory Cards
    function appendStartCard(data) {
        const card = document.createElement("div");
        card.className = "step-card";
        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag tag-reasoning"><i class="fa-solid fa-play"></i> User Query Initialized</span>
                <span class="step-num">START</span>
            </div>
            <div class="step-content">
                <strong>Query:</strong> "${escapeHtml(data.query)}"
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendReasoningCard(data) {
        const card = document.createElement("div");
        card.className = "step-card";
        
        let toolCallSnippet = "";
        if (data.tool_calls && data.tool_calls.length > 0) {
            toolCallSnippet = `<div class="code-block">🔧 Tool Decision: ${escapeHtml(JSON.stringify(data.tool_calls, null, 2))}</div>`;
        }

        const textContent = typeof data.content === "string" ? data.content : JSON.stringify(data.content);

        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag tag-reasoning"><i class="fa-solid fa-brain"></i> LLM Reasoning (call_model)</span>
                <span class="step-num">Step ${data.step || 1}</span>
            </div>
            <div class="step-content">
                ${data.thought ? `<p><em>Thought:</em> ${escapeHtml(data.thought)}</p>` : ''}
                ${textContent ? `<p>${escapeHtml(textContent)}</p>` : ''}
                ${toolCallSnippet}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendToolCallCard(data) {
        const card = document.createElement("div");
        card.className = "step-card";
        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag tag-tool"><i class="fa-solid fa-wrench"></i> Invoking Tool: ${escapeHtml(data.tool)}</span>
                <span class="step-num">Step ${data.step || 1}</span>
            </div>
            <div class="step-content">
                <div class="code-block">Input Arguments: ${escapeHtml(JSON.stringify(data.args, null, 2))}</div>
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendToolResultCard(data) {
        const card = document.createElement("div");
        card.className = "step-card";
        const outputStr = typeof data.output === "string" ? data.output : JSON.stringify(data.output, null, 2);
        
        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag tag-result"><i class="fa-solid fa-check-double"></i> Tool Result: ${escapeHtml(data.tool)}</span>
                <span class="step-num">Observation</span>
            </div>
            <div class="step-content">
                <div class="code-block">${escapeHtml(outputStr)}</div>
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendFinalAnswerCard(data) {
        const card = document.createElement("div");
        card.className = "step-card";
        const textContent = typeof data.content === "string" ? data.content : JSON.stringify(data.content);

        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag tag-final"><i class="fa-solid fa-flag-checkered"></i> Final Response</span>
                <span class="step-num">END</span>
            </div>
            <div class="step-content" style="font-size: 14px; line-height: 1.6;">
                ${formatMarkdown(escapeHtml(textContent))}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendErrorCard(msg) {
        const card = document.createElement("div");
        card.className = "step-card";
        card.style.borderColor = "var(--accent-red)";
        card.innerHTML = `
            <div class="step-header">
                <span class="step-tag" style="color: var(--accent-red);"><i class="fa-solid fa-triangle-exclamation"></i> Execution Error</span>
            </div>
            <div class="step-content" style="color: var(--accent-red);">
                ${escapeHtml(msg)}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function scrollToBottom() {
        trajectoryFeed.scrollTop = trajectoryFeed.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatMarkdown(text) {
        if (!text) return "";
        return text
            .replace(/\n\n/g, "<br><br>")
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>");
    }
});
