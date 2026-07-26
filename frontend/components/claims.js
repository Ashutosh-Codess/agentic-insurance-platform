function formatMoney(amount) {
  if (amount === null || amount === undefined) return "-";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
}

function renderClaimCard(claim, options = {}) {
  const { agentView = false, showActions = false } = options;
  const claimId = claim.id;

  const meta = `
    <div class="claim-meta">
      <div><div class="label">Claim ID</div><code>${claimId}</code></div>
      <div><div class="label">Type</div>${claim.type}</div>
      <div><div class="label">Amount</div>${formatMoney(claim.claimed_amount)}</div>
      <div><div class="label">Submitted</div>${new Date(claim.submitted_at).toLocaleString()}</div>
      ${claim.approved_amount != null ? `<div><div class="label">Approved</div>${formatMoney(claim.approved_amount)}</div>` : ""}
      ${claim.fraud_score != null ? `<div><div class="label">Fraud Score</div>${claim.fraud_score}</div>` : ""}
    </div>
  `;

  const decision = claim.final_decision
    ? `<p class="muted"><strong>Decision notes:</strong> ${claim.final_decision}</p>`
    : "";

  const actions = showActions
    ? `
      <div class="btn-row" data-claim-actions="${claimId}">
        <button class="small secondary" onclick="runAnalysis('${claimId}')">Run AI Analysis</button>
        <button class="small success" onclick="quickDecision('${claimId}', 'approved')">Approve</button>
        <button class="small danger" onclick="quickDecision('${claimId}', 'rejected')">Reject</button>
      </div>
      <div id="analysis-${claimId}" class="analysis-box" style="display:none;"></div>
    `
    : "";

  return `
    <div class="card" id="claim-${claimId}">
      <div class="claim-card-header">
        <div>
          <strong>${claim.type.charAt(0).toUpperCase() + claim.type.slice(1)} Claim</strong>
          ${agentView && claim.customer_name ? `<p class="muted">Customer: ${claim.customer_name}</p>` : ""}
        </div>
        <span class="badge ${claim.status}">${claim.status}</span>
      </div>
      <p class="muted">${claim.incident_description || "No description provided."}</p>
      ${meta}
      ${decision}
      ${actions}
    </div>
  `;
}

function renderClaimsList(containerId, claims, options = {}) {
  const container = document.getElementById(containerId);
  if (!claims.length) {
    container.innerHTML = `<div class="empty-state"><p>No claims to show yet.</p></div>`;
    return;
  }
  container.innerHTML = claims.map((c) => renderClaimCard(c, options)).join("");
}
