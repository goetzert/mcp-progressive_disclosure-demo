/**
 * Progressive Disclosure Demo — Frontend logic.
 *
 * Communicates with the backend via ``POST /api/demo`` and renders
 * side-by-side comparison panels, flow visualisations, and a token-reduction
 * bar chart.
 */

const API_BASE = "";
const DEFAULT_PROMPT = "Wie ist das Wetter in Leipzig?";

/**
 * Shorthand for ``document.getElementById``.
 * @param {string} id — Element ID.
 * @returns {HTMLElement}
 */
const el = (id) => document.getElementById(id);

/**
 * Set a placeholder message inside a panel's flow area.
 * @param {string} panelId — Panel prefix (``"normal"`` or ``"progressive"``).
 * @param {string} text — Placeholder text to display.
 */
function setPlaceholder(panelId, text) {
    const flow = el(`${panelId}-flow`);
    flow.innerHTML = `<div class="placeholder">${text}</div>`;
}

/**
 * Append a flow step to a panel's flow area, removing any existing placeholder.
 * @param {string} panelId — Panel prefix.
 * @param {string} stepHtml — HTML string for the flow step.
 */
function appendFlowStep(panelId, stepHtml) {
    const flow = el(`${panelId}-flow`);
    const placeholder = flow.querySelector(".placeholder");
    if (placeholder) placeholder.remove();
    flow.innerHTML += stepHtml;
}

/**
 * Render the naive (normal) mode result into the left panel.
 * Updates metrics, flow steps, and the answer box.
 * @param {Object} data — Result dict from the backend for the naive mode.
 */
function renderNormalResult(data) {
    el("normal-tools-available").textContent = data.tools_available;
    el("normal-tools-sent").textContent = data.tools_sent_to_llm;
    el("normal-schema-tokens").textContent = data.schema_tokens.toLocaleString();
    el("normal-total-tokens").textContent = data.total_tokens.toLocaleString();

    const flow = el("normal-flow");
    flow.innerHTML = "";

    data.steps.forEach((step) => {
        if (step.description.includes("Fetch")) {
            appendFlowStep("normal", `<div class="flow-step">↓ Fetch all ${step.tools_count} tools from MCP</div>`);
        } else if (step.description.includes("Send all")) {
            appendFlowStep("normal", `<div class="flow-step">↓ Send ${step.tools_sent_to_llm} tool schemas to LLM</div>`);
            appendFlowStep("normal", `<div class="flow-step">Schema tokens: ${step.schema_tokens.toLocaleString()}</div>`);
        } else if (step.tool_name) {
            appendFlowStep("normal", `<div class="flow-step tool-call">↓ LLM calls: ${step.tool_name}(${JSON.stringify(step.tool_arguments)})</div>`);
            appendFlowStep("normal", `<div class="flow-step">↓ Execute via MCP → result received</div>`);
        } else if (step.answer) {
            const answerBox = el("normal-answer");
            answerBox.style.display = "block";
            answerBox.innerHTML = `<div class="answer-label">ANSWER</div>${step.answer}`;
        }
    });
}

/**
 * Render the progressive mode result into the right panel.
 * Updates metrics, flow steps (including search and candidate steps),
 * and the answer box.
 * @param {Object} data — Result dict from the backend for the progressive mode.
 */
function renderProgressiveResult(data) {
    el("progressive-tools-available").textContent = data.tools_available;
    el("progressive-tools-sent").textContent = data.tools_sent_to_llm;
    el("progressive-schema-tokens").textContent = data.schema_tokens.toLocaleString();
    el("progressive-total-tokens").textContent = data.total_tokens.toLocaleString();

    const flow = el("progressive-flow");
    flow.innerHTML = "";

    data.steps.forEach((step) => {
        if (step.description.includes("Fetch")) {
            appendFlowStep("progressive", `<div class="flow-step">↓ Fetch all ${step.tools_count} tools (search index)</div>`);
        } else if (step.description.includes("Send only")) {
            appendFlowStep("progressive", `<div class="flow-step">↓ Send only search_tools schema (1 tool)</div>`);
            appendFlowStep("progressive", `<div class="flow-step">Schema tokens: ${step.schema_tokens.toLocaleString()}</div>`);
        } else if (step.search_query) {
            appendFlowStep("progressive", `<div class="flow-step tool-call">↓ LLM calls: search_tools(query="${step.search_query}")</div>`);
            appendFlowStep("progressive", `<div class="flow-step candidates">↓ Found ${step.candidates_found} candidates: ${step.candidate_names.join(", ")}</div>`);
        } else if (step.tool_name) {
            appendFlowStep("progressive", `<div class="flow-step tool-call">↓ LLM calls: ${step.tool_name}(${JSON.stringify(step.tool_arguments)})</div>`);
            appendFlowStep("progressive", `<div class="flow-step">↓ Execute via MCP → result received</div>`);
        } else if (step.answer) {
            const answerBox = el("progressive-answer");
            answerBox.style.display = "block";
            answerBox.innerHTML = `<div class="answer-label">ANSWER</div>${step.answer}`;
        }
    });
}

/**
 * Render the token-reduction bar chart comparing naive vs. progressive totals.
 * @param {number} naiveTotal — Total tokens from the naive mode.
 * @param {number} progressiveTotal — Total tokens from the progressive mode.
 */
function renderChart(naiveTotal, progressiveTotal) {
    const maxTokens = Math.max(naiveTotal, progressiveTotal, 1);
    const container = el("chart-container");
    container.innerHTML = "";

    const rows = [
        { label: "Normal", value: naiveTotal, cls: "normal" },
        { label: "Progressive", value: progressiveTotal, cls: "progressive" },
    ];

    rows.forEach((row) => {
        const widthPct = (row.value / maxTokens) * 100;
        const rowHtml = `
            <div class="bar-row">
                <div class="bar-label">${row.label}</div>
                <div class="bar-track">
                    <div class="bar-fill ${row.cls}" style="width: ${widthPct}%"></div>
                </div>
                <div class="bar-value">${row.value.toLocaleString()}</div>
            </div>
        `;
        container.innerHTML += rowHtml;
    });

    if (naiveTotal > 0 && progressiveTotal > 0) {
        const reduction = ((1 - progressiveTotal / naiveTotal) * 100).toFixed(1);
        el("reduction-info").textContent = `−${reduction}% token reduction`;
    }
}

/**
 * Run the demo: send the user's prompt to the backend, then render results
 * for both modes and the token-reduction chart.
 * Disables the run button while the request is in flight.
 * @returns {Promise<void>}
 */
async function runDemo() {
    const prompt = el("prompt-input").value.trim();
    if (!prompt) return;

    const btn = el("run-btn");
    btn.disabled = true;
    btn.textContent = "Running…";

    setPlaceholder("normal", "Running…");
    setPlaceholder("progressive", "Waiting…");

    try {
        const response = await fetch(`${API_BASE}/api/demo`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: prompt }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();

        renderNormalResult(result.naive);
        renderProgressiveResult(result.progressive);
        renderChart(
            result.naive.total_tokens,
            result.progressive.total_tokens
        );
    } catch (err) {
        setPlaceholder("normal", `Error: ${err.message}`);
        setPlaceholder("progressive", `Error: ${err.message}`);
        console.error("Demo error:", err);
    } finally {
        btn.disabled = false;
        btn.textContent = "Run";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    el("run-btn").addEventListener("click", runDemo);
    el("prompt-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") runDemo();
    });
});
