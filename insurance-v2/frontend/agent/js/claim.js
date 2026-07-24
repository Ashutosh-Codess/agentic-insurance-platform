/**
 * Claim detail page: full AI analysis breakdown, decision buttons, and
 * the keyword-grounded Insurance Copilot panel.
 */

async function renderClaimDetail(claimId) {
  const app = document.getElementById("app");
  app.innerHTML = `${nav("queue")}<div class="page">Loading…</div>`;
  const claim = await Api.get(`/agents/claims/${claimId}`);
  const analysis = claim.ai_analysis || {};

  app.innerHTML = `
    ${nav("queue")}
    <div class="page">
      <div class="grid-3">
        <div>
          <h1>Claim ${claim.id.slice(0, 8)}…</h1>
          <p class="muted">${claim.claim_type} · Claimed ${claim.claimed_amount} · Status <b>${claim.status}</b></p>

          ${
            analysis.document_quality
              ? `<div class="card"><h2>Document Quality</h2><p class="muted">${JSON.stringify(analysis.document_quality)}</p></div>`
              : ""
          }
          ${
            analysis.damage_detection
              ? `<div class="card"><h2>Damage Detection</h2><p class="muted">Score ${analysis.damage_detection.damage_score} (${analysis.damage_detection.method}) — ${analysis.damage_detection.reason}</p></div>`
              : ""
          }
          ${
            analysis.fraud
              ? `<div class="card"><h2>Fraud Analysis — Score ${analysis.fraud.fraud_score}</h2><p class="muted">${analysis.fraud.reasoning}</p></div>`
              : ""
          }
          ${
            analysis.classification
              ? `<div class="card"><h2>Classification</h2><p class="muted">${analysis.classification.claim_class} (confidence ${analysis.classification.confidence}, ${analysis.classification.method})</p></div>`
              : ""
          }

          ${
            analysis.decision
              ? `<div class="card">
                  <h2>Decision Recommendation: ${analysis.decision.recommended_action.toUpperCase()}</h2>
                  <p class="muted">Confidence: ${analysis.decision.confidence}</p>
                  <p class="muted">${analysis.decision.reasoning}</p>
                  ${
                    claim.final_action
                      ? `<p style="color:#86efac;">Final action recorded: ${claim.final_action}</p>`
                      : `<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
                          <button class="btn-primary" onclick="decideClaim('${claim.id}','approve')">Approve</button>
                          <button class="btn-danger" onclick="decideClaim('${claim.id}','reject')">Reject</button>
                          <button class="btn-warn" onclick="decideClaim('${claim.id}','escalate')">Escalate further</button>
                        </div>`
                  }
                </div>`
              : `<div class="card">
                  <p class="muted">No AI analysis yet for this claim.</p>
                  <button class="btn-primary" onclick="runProcessing('${claim.id}')">Run AI processing</button>
                </div>`
          }
        </div>

        <div class="card" style="height:fit-content;">
          <h2>Insurance Copilot</h2>
          <div id="copilot-answer" class="muted" style="white-space:pre-line; max-height:280px; overflow-y:auto; margin-bottom:0.75rem;"></div>
          <textarea id="copilot-question" placeholder="Why is fraud risk high? Which clause applies?"></textarea>
          <button class="btn-primary" style="width:100%" onclick="askCopilot('${claim.id}')">Ask</button>
        </div>
      </div>
    </div>
  `;
}

async function runProcessing(claimId) {
  try {
    await Api.post(`/claims/${claimId}/process`);
    renderClaimDetail(claimId);
  } catch (e) {
    alert(e.message);
  }
}

async function decideClaim(claimId, action) {
  try {
    await Api.post(`/agents/claims/${claimId}/decision`, { final_action: action });
    renderClaimDetail(claimId);
  } catch (e) {
    alert(e.message);
  }
}

async function askCopilot(claimId) {
  const question = document.getElementById("copilot-question").value;
  if (!question) return;
  const box = document.getElementById("copilot-answer");
  box.textContent = "Thinking…";
  try {
    const result = await Api.post(`/claims/${claimId}/copilot`, { question });
    box.innerHTML = `<div>${result.answer}</div><div class="muted" style="margin-top:0.5rem;">Sources: ${result.sources.join(", ")}</div>`;
  } catch (e) {
    box.textContent = e.message;
  }
}
