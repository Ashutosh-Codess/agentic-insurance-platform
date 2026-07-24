/**
 * Agent dashboard (aggregate stats + pending queue) and the full,
 * filterable claim queue.
 */

async function renderDashboard() {
  const app = document.getElementById("app");
  const [stats, pending] = await Promise.all([
    Api.get("/agents/dashboard"),
    Api.get("/agents/claims?pending_only=true"),
  ]);

  app.innerHTML = `
    ${nav("dashboard")}
    <div class="page">
      <div class="grid-4">
        <div class="card"><div class="stat-label">Today</div><div class="stat-value">${stats.today_count}</div></div>
        <div class="card"><div class="stat-label">Pending</div><div class="stat-value">${stats.pending_count}</div></div>
        <div class="card"><div class="stat-label">High Risk</div><div class="stat-value" style="color:#f87171">${stats.high_risk_count}</div></div>
        <div class="card"><div class="stat-label">Avg processing (hrs)</div><div class="stat-value">${stats.avg_processing_time_hours ?? "—"}</div></div>
      </div>

      <h2>Pending Claims</h2>
      <div id="claims-list">${pending.map(renderQueueCard).join("") || `<p class="muted">Nothing pending.</p>`}</div>
    </div>
  `;
}

function renderQueueCard(c) {
  const fraud = (c.ai_analysis || {}).fraud;
  const isHighRisk = fraud && fraud.fraud_score >= 0.75;
  return `
    <div class="card" onclick="location.hash='#/claims/${c.id}'" style="cursor:pointer;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong>Claim ${c.id.slice(0, 8)}… — ${c.claim_type}</strong>
        <span class="badge ${isHighRisk ? "badge-high-risk" : "badge-normal"}">
          ${isHighRisk ? "High Risk" : "Normal"}${fraud ? ` · Fraud ${fraud.fraud_score}` : ""}
        </span>
      </div>
      <p class="muted">Claimed: ${c.claimed_amount} · Status: ${c.status}</p>
    </div>
  `;
}

async function renderQueue() {
  const app = document.getElementById("app");
  app.innerHTML = `${nav("queue")}<div class="page">Loading…</div>`;
  const claims = await Api.get("/agents/claims");

  app.innerHTML = `
    ${nav("queue")}
    <div class="page">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h1>All Claims</h1>
        <button class="btn-link" onclick="filterHighRisk()">Show high-risk only</button>
      </div>
      <div id="claims-list">${claims.map(renderQueueCard).join("") || `<p class="muted">No claims yet.</p>`}</div>
    </div>
  `;
}

async function filterHighRisk() {
  const claims = await Api.get("/agents/claims?high_risk_only=true");
  document.getElementById("claims-list").innerHTML =
    claims.map(renderQueueCard).join("") || `<p class="muted">No high-risk claims.</p>`;
}
