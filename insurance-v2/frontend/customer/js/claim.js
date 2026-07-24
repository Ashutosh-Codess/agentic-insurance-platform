/**
 * Claim submission, document upload, and triggering the AI pipeline.
 */

async function renderClaims() {
  const app = document.getElementById("app");
  const [claims, policies] = await Promise.all([Api.get("/customers/me/claims"), Api.get("/customers/me/policies")]);

  app.innerHTML = `
    ${nav("claims")}
    <div class="page">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h1>Claims</h1>
        <button class="btn-primary" onclick="toggleNewClaimForm()">+ Submit a Claim</button>
      </div>

      <div id="new-claim-form" class="card hidden">
        <h2>Submit a Claim</h2>
        <select id="claim-policy">
          ${policies.map((p) => `<option value="${p.id}">${p.id.slice(0, 8)}… (${p.status})</option>`).join("")}
        </select>
        <select id="claim-type">
          <option value="health">Health</option>
          <option value="life">Life</option>
          <option value="motor">Motor</option>
          <option value="travel">Travel</option>
          <option value="home">Home</option>
          <option value="business">Business</option>
        </select>
        <input id="claim-amount" type="number" placeholder="Claimed amount" />
        <textarea id="claim-description" placeholder="Description"></textarea>
        <button class="btn-primary" onclick="submitClaimForm()">Submit</button>
      </div>

      <div id="claims-list">
        ${claims.map(renderClaimCard).join("") || `<p class="muted">No claims yet.</p>`}
      </div>
    </div>
  `;
}

function renderClaimCard(c) {
  const decision = (c.ai_analysis || {}).decision;
  const fraud = (c.ai_analysis || {}).fraud;
  return `
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong>${c.claim_type} — ${c.claimed_amount}</strong>
        <span class="badge badge-status">${c.status}</span>
      </div>
      <p class="muted">${c.description || ""}</p>
      <div style="display:flex; gap:0.5rem; align-items:center; margin-top:0.5rem;">
        <input type="file" id="doc-file-${c.id}" style="width:auto;" />
        <select id="doc-type-${c.id}" style="width:auto;">
          <option value="invoice">Invoice</option>
          <option value="medical_report">Medical Report</option>
          <option value="hospital_bill">Hospital Bill</option>
          <option value="photo">Photo (for motor damage detection)</option>
          <option value="receipt">Receipt</option>
        </select>
        <button class="btn-link" onclick="uploadClaimDoc('${c.id}')">Upload</button>
        <button class="btn-primary" style="margin-left:auto;" onclick="processClaim('${c.id}')">Run AI processing</button>
      </div>
      ${fraud ? `<p class="muted" style="margin-top:0.5rem;">Fraud score: <b>${fraud.fraud_score}</b> — ${fraud.reasoning}</p>` : ""}
      ${decision ? `<p class="muted">AI recommendation: <b>${decision.recommended_action}</b> (confidence ${decision.confidence}) — ${decision.reasoning}</p>` : ""}
    </div>
  `;
}

function toggleNewClaimForm() {
  document.getElementById("new-claim-form").classList.toggle("hidden");
}

async function submitClaimForm() {
  const policy_id = document.getElementById("claim-policy").value;
  const claim_type = document.getElementById("claim-type").value;
  const claimed_amount = parseFloat(document.getElementById("claim-amount").value);
  const description = document.getElementById("claim-description").value;
  try {
    await Api.post("/claims", { policy_id, claim_type, claimed_amount, description });
    renderClaims();
  } catch (e) {
    alert(e.message);
  }
}

async function uploadClaimDoc(claimId) {
  const file = document.getElementById(`doc-file-${claimId}`).files[0];
  const docType = document.getElementById(`doc-type-${claimId}`).value;
  if (!file) return;
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  await Api.postForm(`/claims/${claimId}/documents`, form);
  renderClaims();
}

async function processClaim(claimId) {
  try {
    await Api.post(`/claims/${claimId}/process`);
    renderClaims();
  } catch (e) {
    alert(e.message);
  }
}
