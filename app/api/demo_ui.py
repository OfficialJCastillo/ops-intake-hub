from fastapi.responses import HTMLResponse


def render_demo_ui() -> HTMLResponse:
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ops-intake-hub demo UI</title>
  <style>
    :root {
      --bg: #eef3ed;
      --panel: #fbfdf8;
      --ink: #13211b;
      --muted: #55645d;
      --accent: #1d6b57;
      --accent-2: #d6efe5;
      --border: #c8d6cf;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(29, 107, 87, 0.12), transparent 26%),
        linear-gradient(180deg, #f7fbf7 0%, var(--bg) 100%);
    }
    main {
      max-width: 1100px;
      margin: 0 auto;
      padding: 44px 20px 56px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(2.3rem, 4vw, 4rem);
      line-height: 0.95;
      max-width: 9ch;
    }
    .eyebrow {
      color: var(--accent);
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 0.8rem;
    }
    .subtitle {
      max-width: 62ch;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 28px;
    }
    .layout {
      display: grid;
      gap: 20px;
      grid-template-columns: minmax(310px, 390px) minmax(0, 1fr);
    }
    .panel {
      background: rgba(251, 253, 248, 0.95);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 18px 36px rgba(16, 39, 29, 0.08);
    }
    label {
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
      font-weight: 700;
      font-size: 0.92rem;
    }
    textarea, input {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px 16px;
      font: inherit;
      background: white;
      color: var(--ink);
    }
    textarea { min-height: 160px; resize: vertical; }
    button {
      border: 0;
      border-radius: 999px;
      padding: 14px 18px;
      background: linear-gradient(135deg, #1d6b57 0%, #0e5a71 100%);
      color: white;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }
    .status { min-height: 1.2rem; margin-top: 12px; color: var(--muted); }
    .status.error { color: #a0224b; }
    .result-grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .card {
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      background: linear-gradient(180deg, var(--panel) 0%, #f2f8f3 100%);
    }
    .card.full { grid-column: 1 / -1; }
    .placeholder {
      color: var(--muted);
      line-height: 1.5;
      border: 1px dashed var(--border);
      border-radius: 18px;
      padding: 20px;
      background: rgba(255,255,255,0.55);
    }
    .section-divider {
      border-top: 1px solid var(--border);
      margin: 22px 0;
    }
    .badge-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
    .badge {
      background: var(--accent-2);
      color: #124838;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.9rem;
      font-weight: 700;
    }
    h2, h3 { margin-top: 0; }
    ul, ol { margin: 0; padding-left: 20px; }
    li { margin-bottom: 10px; line-height: 1.45; }
    @media (max-width: 920px) {
      .layout, .result-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">Operational intake before execution</div>
    <h1>ops-intake-hub demo UI</h1>
    <p class="subtitle">
      Preview how messy requests get normalized into category, priority, queue, owner, deadline window,
      missing fields, and immediate next actions before anyone starts doing work.
    </p>

    <section class="layout">
      <form class="panel" id="intake-form">
        <label>
          Title
          <input id="title" value="Customer outage on billing portal" />
        </label>
        <label>
          Details
          <textarea id="details">Multiple customers report the billing portal is down and finance cannot process invoices today. We may need a rollback.</textarea>
        </label>
        <label>
          Source
          <input id="source" value="slack" />
        </label>
        <label>
          Requester team
          <input id="requester_team" value="Finance Operations" />
        </label>
        <label>
          Affected system
          <input id="affected_system" value="billing-portal" />
        </label>
        <button type="submit" id="submit">Assess intake</button>
        <p class="status" id="status" aria-live="polite"></p>
      </form>

      <section class="panel">
        <h2>Triage preview</h2>
        <div id="results" class="placeholder">
          Submit a request to see queue, priority, owner, risks, missing fields, and next actions.
        </div>
        <div class="section-divider"></div>
        <h2>Triage rules</h2>
        <div id="rules" class="placeholder">
          Loading deterministic SLA policy and category rules from <code>GET /triage/rules</code>.
        </div>
      </section>
    </section>
  </main>

  <script>
    const form = document.getElementById("intake-form");
    const statusNode = document.getElementById("status");
    const resultNode = document.getElementById("results");
    const rulesNode = document.getElementById("rules");
    const submitButton = document.getElementById("submit");

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderList(items, ordered) {
      const tag = ordered ? "ol" : "ul";
      if (!items || items.length === 0) {
        return "<p>No items returned.</p>";
      }
      return `<${tag}>${items.map((item) => `<li>${item}</li>`).join("")}</${tag}>`;
    }

    function renderAssessment(data) {
      resultNode.className = "result-grid";
      resultNode.innerHTML = `
        <section class="card full">
          <div class="badge-row">
            <span class="badge">Category: ${escapeHtml(data.triage_category.replaceAll("_", " "))}</span>
            <span class="badge">Priority: ${escapeHtml(data.priority)}</span>
            <span class="badge">Queue: ${escapeHtml(data.queue)}</span>
          </div>
          <p>${escapeHtml(data.summary)}</p>
          <p><strong>Recommended owner:</strong> ${escapeHtml(data.recommended_owner)}</p>
          <p><strong>Due window:</strong> ${escapeHtml(data.due_window)}</p>
          <p><strong>SLA policy:</strong> ${escapeHtml(data.sla_policy)}</p>
        </section>
        <section class="card">
          <h3>Next actions</h3>
          ${renderList(data.next_actions.map(escapeHtml), true)}
        </section>
        <section class="card">
          <h3>Missing fields</h3>
          ${renderList(data.missing_fields.map(escapeHtml), false)}
        </section>
        <section class="card">
          <h3>Risk flags</h3>
          ${renderList(data.risk_flags.map(escapeHtml), false)}
        </section>
        <section class="card full">
          <h3>Routing rationale</h3>
          ${renderList(data.routing_rationale.map(escapeHtml), false)}
        </section>
      `;
    }

    function renderRules(data) {
      const priorityRows = Object.entries(data.priority_due_windows).map(
        ([priority, window]) => `<strong>${escapeHtml(priority)}</strong>: ${escapeHtml(window)}`
      );
      const categoryRows = data.category_rules.map((rule) => `
        <strong>${escapeHtml(rule.triage_category.replaceAll("_", " "))}</strong>
        routes to ${escapeHtml(rule.queue)} with ${escapeHtml(rule.recommended_owner)} as owner.
        Required intake: ${escapeHtml(rule.required_fields.join(", "))}.
      `);

      rulesNode.className = "result-grid";
      rulesNode.innerHTML = `
        <section class="card">
          <h3>SLA windows</h3>
          ${renderList(priorityRows, false)}
        </section>
        <section class="card">
          <h3>Category rules</h3>
          ${renderList(categoryRows, false)}
        </section>
      `;
    }

    async function loadRules() {
      const response = await fetch("/triage/rules");
      const data = await response.json();
      if (!response.ok) {
        throw new Error("Unable to load triage rules.");
      }
      renderRules(data);
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submitButton.disabled = true;
      statusNode.className = "status";
      statusNode.textContent = "Assessing intake...";
      const payload = {
        title: document.getElementById("title").value,
        details: document.getElementById("details").value,
        source: document.getElementById("source").value,
        requester_team: document.getElementById("requester_team").value || null,
        affected_system: document.getElementById("affected_system").value || null,
      };
      try {
        const response = await fetch("/triage/assess", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(typeof data.detail === "string" ? data.detail : "Request failed.");
        }
        renderAssessment(data);
        statusNode.textContent = "Assessment generated from the live API.";
      } catch (error) {
        resultNode.className = "placeholder";
        resultNode.textContent = "Unable to render triage assessment. Check the request fields and try again.";
        statusNode.className = "status error";
        statusNode.textContent = error.message;
      } finally {
        submitButton.disabled = false;
      }
    });

    loadRules().catch((error) => {
      rulesNode.className = "placeholder";
      rulesNode.textContent = error.message;
    });
  </script>
</body>
</html>
        """
    )
