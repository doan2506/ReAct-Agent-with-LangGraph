/**
 * Client JavaScript Logic for LangGraph ReAct Agent UI
 * Renders ReAct Trajectory in separate User / Thought / Action / Observation / Output box cards.
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

    const trajectoryFeed = document.getElementById("trajectoryFeed");
    const emptyState = document.getElementById("emptyState");

    let eventSource = null;

    // Fetch API status & models on load
    fetchConfig();

    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            if (data.models && modelSelect) {
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

    // Sample Prompt Pills Handler
    document.querySelectorAll(".pill-btn").forEach(pill => {
        pill.addEventListener("click", () => {
            const prompt = pill.getAttribute("data-prompt");
            if (promptInput) promptInput.value = prompt;
            startReActLoop();
        });
    });

    // Clear Stream Button
    if (clearBtn) {
        clearBtn.addEventListener("click", resetStreamView);
    }

    function resetStreamView() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        if (trajectoryFeed) {
            trajectoryFeed.innerHTML = "";
            if (emptyState) {
                trajectoryFeed.appendChild(emptyState);
                emptyState.style.display = "flex";
            }
        }

        updateStatus("Ready", "idle");
    }

    function updateStatus(text, state) {
        if (statusText) statusText.textContent = text;
        if (statusBadge) statusBadge.className = `status-badge ${state}`;
    }

    // Run Button Click Handler
    if (runBtn) {
        runBtn.addEventListener("click", startReActLoop);
    }

    function startReActLoop() {
        if (!promptInput) return;
        const query = promptInput.value.trim();
        if (!query) return;

        resetStreamView();
        if (emptyState) emptyState.style.display = "none";

        updateStatus("Running...", "running");

        const params = new URLSearchParams({
            query: query,
            model: modelSelect ? modelSelect.value : "google_genai/gemini-3.5-flash-lite",
            system_prompt: systemPrompt ? systemPrompt.value : "You are a helpful ReAct AI assistant.",
            simulation: (simToggle && simToggle.checked) ? "true" : "false"
        });

        eventSource = new EventSource(`/api/stream?${params.toString()}`);

        eventSource.addEventListener("start", (e) => {
            const data = JSON.parse(e.data);
            appendUserQuery(data.query);
        });

        eventSource.addEventListener("reasoning", (e) => {
            const data = JSON.parse(e.data);
            appendReasoningStep(data);
        });

        eventSource.addEventListener("tool_result", (e) => {
            const data = JSON.parse(e.data);
            appendObservationStep(data);
        });

        eventSource.addEventListener("final_answer", (e) => {
            const data = JSON.parse(e.data);
            appendFinalAnswerStep(data);
        });

        eventSource.addEventListener("complete", () => {
            updateStatus("Completed", "completed");
            if (eventSource) eventSource.close();
        });

        eventSource.addEventListener("error", (e) => {
            let errMsg = "An error occurred during execution.";
            try {
                if (e.data) errMsg = JSON.parse(e.data).error || errMsg;
            } catch (err) {}
            appendErrorStep(errMsg);
            updateStatus("Error Encountered", "idle");
            if (eventSource) eventSource.close();
        });
    }

    // Render Separate ReAct Step Box Cards
    function appendUserQuery(queryText) {
        if (!trajectoryFeed) return;
        const card = document.createElement("div");
        card.className = "step-card";
        card.innerHTML = `
            <div class="react-line react-user">
                <span class="react-label">User:</span> ${escapeHtml(queryText)}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function formatActionArgs(args) {
        if (!args) return "";
        if (typeof args === "string") return args;
        if (typeof args === "object") {
            if (args.query) return args.query;
            const keys = Object.keys(args);
            if (keys.length === 1) {
                return String(args[keys[0]]);
            }
            return keys.map(k => {
                let v = args[k];
                if (typeof v === "object") v = JSON.stringify(v);
                return `${k}="${v}"`;
            }).join(", ");
        }
        return String(args);
    }

    function appendReasoningStep(data) {
        if (!trajectoryFeed) return;

        let thoughtText = data.thought || (typeof data.content === "string" ? data.content : "");
        if (!thoughtText && data.tool_calls && data.tool_calls.length > 0) {
            const toolNames = data.tool_calls.map(c => c.name).join(", ");
            thoughtText = `I will execute tool(s): ${toolNames}`;
        }

        // 1. Separate Single Box for Thought (Appears immediately)
        if (thoughtText) {
            const thoughtCard = document.createElement("div");
            thoughtCard.className = "step-card";
            thoughtCard.innerHTML = `
                <div class="react-line react-thought">
                    <span class="react-label">Thought:</span> ${escapeHtml(thoughtText)}
                </div>
            `;
            trajectoryFeed.appendChild(thoughtCard);
            scrollToBottom();
        }

        // 2. Separate Single Box for Action (Appears with 350ms staggered delay per tool call)
        if (data.tool_calls && data.tool_calls.length > 0) {
            data.tool_calls.forEach((call, index) => {
                setTimeout(() => {
                    const actionCard = document.createElement("div");
                    actionCard.className = "step-card";
                    const argStr = formatActionArgs(call.args);
                    actionCard.innerHTML = `
                        <div class="react-line react-action">
                            <span class="react-label">Action:</span> <span class="action-fn">${escapeHtml(call.name)}</span>(${escapeHtml(argStr)})
                        </div>
                    `;
                    trajectoryFeed.appendChild(actionCard);
                    scrollToBottom();
                }, (index + 1) * 350);
            });
        }
    }

    function appendObservationStep(data) {
        if (!trajectoryFeed) return;
        const card = document.createElement("div");
        card.className = "step-card";
        
        let raw = data.output;
        let parsed = raw;

        // Try parsing JSON string if applicable
        if (typeof raw === "string") {
            try {
                parsed = JSON.parse(raw);
            } catch (e) {
                parsed = raw;
            }
        }

        let formattedText = "";

        // If parsed is array of email / tool result objects
        if (Array.isArray(parsed) && parsed.length > 0 && typeof parsed[0] === "object") {
            formattedText = parsed.map((item, idx) => {
                const textSnippet = item.snippet || item.body || item.subject || item.title || JSON.stringify(item);
                return `${idx + 1}. ${textSnippet}`;
            }).join("\n");
        } else if (typeof parsed === "object" && parsed !== null) {
            formattedText = parsed.snippet || parsed.body || parsed.text || JSON.stringify(parsed);
        } else {
            formattedText = String(parsed);
        }

        // Truncate long observations to 350 characters
        const MAX_OBSERVATION_LENGTH = 350;
        if (formattedText.length > MAX_OBSERVATION_LENGTH) {
            formattedText = formattedText.substring(0, MAX_OBSERVATION_LENGTH) + " ...";
        }

        card.innerHTML = `
            <div class="react-line react-observation">
                <span class="react-label">Observation:</span> ${escapeHtml(formattedText)}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function appendFinalAnswerStep(data) {
        if (!trajectoryFeed) return;

        // 1. Final Thought Box Card
        const thoughtCard = document.createElement("div");
        thoughtCard.className = "step-card";
        thoughtCard.innerHTML = `
            <div class="react-line react-thought">
                <span class="react-label">Thought:</span> I have gathered enough information
            </div>
        `;
        trajectoryFeed.appendChild(thoughtCard);

        // 2. Extract clean text content from message object/string
        let textContent = data.content;
        if (typeof textContent === "object" && textContent !== null) {
            if (textContent.text) {
                textContent = textContent.text;
            } else if (Array.isArray(textContent)) {
                textContent = textContent.map(item => typeof item === "string" ? item : (item.text || "")).join("\n");
            } else {
                textContent = JSON.stringify(textContent);
            }
        }

        // 3. Clean Output Box Card
        const answerCard = document.createElement("div");
        answerCard.className = "step-card";
        answerCard.innerHTML = `
            <div class="react-line">
                <span class="react-label" style="color: var(--accent-cyan);">Output:</span>
                <div style="margin-top: 6px; line-height: 1.6; color: var(--text-main);">
                    ${formatMarkdown(escapeHtml(textContent))}
                </div>
            </div>
        `;
        trajectoryFeed.appendChild(answerCard);
        scrollToBottom();
    }

    function appendErrorStep(msg) {
        if (!trajectoryFeed) return;
        const card = document.createElement("div");
        card.className = "step-card";
        card.style.borderColor = "var(--accent-red)";
        card.innerHTML = `
            <div class="react-line" style="color: var(--accent-red);">
                <span class="react-label" style="color: var(--accent-red);">Error:</span> ${escapeHtml(msg)}
            </div>
        `;
        trajectoryFeed.appendChild(card);
        scrollToBottom();
    }

    function scrollToBottom() {
        if (trajectoryFeed) {
            trajectoryFeed.scrollTop = trajectoryFeed.scrollHeight;
        }
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
        let formatted = text
            // Code blocks ```...```
            .replace(/```([\s\S]*?)```/g, '<div class="code-block">$1</div>')
            // Headers (#, ##, ###)
            .replace(/^### (.*$)/gim, '<h4 style="font-size: 14px; font-weight: 700; color: var(--accent-cyan); margin-top: 10px; margin-bottom: 4px;">$1</h4>')
            .replace(/^## (.*$)/gim, '<h3 style="font-size: 15px; font-weight: 700; color: var(--accent-cyan); margin-top: 12px; margin-bottom: 6px;">$1</h3>')
            .replace(/^# (.*$)/gim, '<h2 style="font-size: 16px; font-weight: 800; color: var(--accent-cyan); margin-top: 14px; margin-bottom: 8px;">$1</h2>')
            // Bold & Italic
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            // Inline code `code`
            .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-family: monospace;">$1</code>')
            // Bullet list items
            .replace(/^\s*[\-\*]\s+(.*$)/gim, '<div style="margin-left: 14px; margin-bottom: 2px;">• $1</div>')
            // Line breaks
            .replace(/\n\n/g, "<br>")
            .replace(/\n/g, "<br>");
        return formatted;
    }
});
