/**
 * Everything except claim-specific screens (see claim.js): dashboard,
 * profile form, product catalog + recommendations, policies list,
 * notifications.
 */

async function renderDashboard() {
  const app = document.getElementById("app");
  app.innerHTML = nav("dashboard") + `<div class="page">Loading...</div>`;

  const [user, policies, claims, recommendations] = await Promise.all([
    Api.get("/customers/me"),
    Api.get("/customers/me/policies"),
    Api.get("/customers/me/claims"),
    Api.get("/customers/me/recommendations"),
  ]);

  const activePolicies = policies.filter((p) => p.status === "active").length;
  const pendingClaims = claims.filter((c) => !["approved", "rejected"].includes(c.status)).length;

  app.innerHTML = `
    ${nav("dashboard")}
    <div class="page">
      <h1>Welcome back, ${user.full_name || user.email}</h1>

      <div class="grid-4">
        <div class="card"><div class="stat-label">Active Policies</div><div class="stat-value">${activePolicies}</div></div>
        <div class="card"><div class="stat-label">Pending Claims</div><div class="stat-value">${pendingClaims}</div></div>
        <div class="card"><div class="stat-label">Risk Score</div><div class="stat-value">${user.risk_score ?? "—"}</div></div>
        <div class="card"><div class="stat-label">Coverage Score</div><div class="stat-value">${user.coverage_score ?? "—"}</div></div>
      </div>

      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h2>AI Recommendations</h2>
          <button class="btn-primary" onclick="refreshRecommendations()">Refresh</button>
        </div>
        <div id="dashboard-recommendations">
          ${
            recommendations.length
              ? recommendations
                  .map(
                    (r) => `
                <div style="border-bottom:1px solid var(--border); padding:0.75rem 0;">
                  <div style="display:flex; justify-content:space-between;">
                    <strong>Product ${r.product_id.slice(0, 8)}…</strong>
                    <span class="muted">score ${r.score}</span>
                  </div>
                  <p class="muted">${r.reasoning}</p>
                  <p>Estimated premium: ${r.estimated_premium}</p>
                </div>`
                  )
                  .join("")
              : `<p class="muted">No recommendations yet — complete your profile, then click Refresh.</p>`
          }
        </div>
      </div>
    </div>
  `;
}

async function refreshRecommendations() {
  const box = document.getElementById("dashboard-recommendations");
  box.innerHTML = `<p class="muted">Running the recommendation engine…</p>`;
  try {
    await Api.post("/customers/me/recommendations/refresh");
  } catch (e) {
    box.innerHTML = `<p class="error-text">${e.message}</p>`;
    return;
  }
  renderDashboard();
}

async function renderProfile() {
  const app = document.getElementById("app");
  const user = await Api.get("/customers/me");
  const health = user.health_data || {};
  const assets = user.assets || {};
  const lifestyle = user.lifestyle_data || {};
  const address = user.address || {};

  app.innerHTML = `
    ${nav("profile")}
    <div class="page" style="max-width:700px;">
      <h1>Your Profile</h1>
      <div id="profile-error" class="error-text"></div>

      <div class="card">
        <h2>Personal</h2>
        <input id="p-name" value="${user.full_name || ""}" placeholder="Full name" />
        <input id="p-dob" type="date" value="${user.date_of_birth || ""}" />
        <input id="p-gender" value="${user.gender || ""}" placeholder="Gender" />
        <input id="p-occupation" value="${user.occupation || ""}" placeholder="Occupation" />
        <input id="p-income" type="number" value="${user.income || ""}" placeholder="Annual income" />
        <input id="p-marital" value="${user.marital_status || ""}" placeholder="Marital status" />
        <input id="p-city" value="${address.city || ""}" placeholder="City" />
      </div>

      <div class="card">
        <h2>Health</h2>
        <div class="checkbox-row"><input id="h-smoking" type="checkbox" ${health.smoking ? "checked" : ""}/> <label for="h-smoking">Smoking</label></div>
        <div class="checkbox-row"><input id="h-alcohol" type="checkbox" ${health.alcohol ? "checked" : ""}/> <label for="h-alcohol">Alcohol</label></div>
        <input id="h-bmi" type="number" step="0.1" value="${health.bmi || ""}" placeholder="BMI" />
        <input id="h-conditions" value="${(health.current_diseases || []).join(", ")}" placeholder="Current conditions (comma separated)" />
      </div>

      <div class="card">
        <h2>Assets</h2>
        <div class="checkbox-row"><input id="a-house" type="checkbox" ${assets.house ? "checked" : ""}/> <label for="a-house">House</label></div>
        <div class="checkbox-row"><input id="a-vehicle" type="checkbox" ${assets.vehicle ? "checked" : ""}/> <label for="a-vehicle">Vehicle</label></div>
        <div class="checkbox-row"><input id="a-business" type="checkbox" ${assets.business ? "checked" : ""}/> <label for="a-business">Business</label></div>
      </div>

      <div class="card">
        <h2>Lifestyle</h2>
        <input id="l-dependents" type="number" value="${lifestyle.dependents || 0}" placeholder="Dependents" />
        <input id="l-risk" value="${lifestyle.risk_appetite || ""}" placeholder="Risk appetite (low/medium/high)" />
      </div>

      <button class="btn-primary" onclick="saveProfile()">Save Profile</button>

      <div class="card" style="margin-top:1.5rem;">
        <h2>KYC Documents</h2>
        <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.75rem;">
          <select id="kyc-type" style="width:auto;">
            <option value="identity_proof">Identity Proof</option>
            <option value="address_proof">Address Proof</option>
            <option value="income_proof">Income Proof</option>
          </select>
          <input id="kyc-file" type="file" style="width:auto;" />
          <button class="btn-primary" onclick="uploadKyc()">Upload</button>
        </div>
        <div id="kyc-list"></div>
      </div>
    </div>
  `;

  loadKycList();
}

async function saveProfile() {
  const payload = {
    full_name: document.getElementById("p-name").value || null,
    date_of_birth: document.getElementById("p-dob").value || null,
    gender: document.getElementById("p-gender").value || null,
    occupation: document.getElementById("p-occupation").value || null,
    income: parseFloat(document.getElementById("p-income").value) || null,
    marital_status: document.getElementById("p-marital").value || null,
    address: { city: document.getElementById("p-city").value },
    health_data: {
      smoking: document.getElementById("h-smoking").checked,
      alcohol: document.getElementById("h-alcohol").checked,
      bmi: parseFloat(document.getElementById("h-bmi").value) || null,
      current_diseases: document
        .getElementById("h-conditions")
        .value.split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    },
    assets: {
      house: document.getElementById("a-house").checked,
      vehicle: document.getElementById("a-vehicle").checked,
      business: document.getElementById("a-business").checked,
    },
    lifestyle_data: {
      dependents: parseInt(document.getElementById("l-dependents").value) || 0,
      risk_appetite: document.getElementById("l-risk").value || null,
    },
  };
  try {
    await Api.put("/customers/me/profile", payload);
    renderProfile();
  } catch (e) {
    document.getElementById("profile-error").textContent = e.message;
  }
}

async function loadKycList() {
  const docs = await Api.get("/customers/me/documents");
  document.getElementById("kyc-list").innerHTML = docs.length
    ? docs.map((d) => `<div class="muted">${d.doc_type} — ${d.status}</div>`).join("")
    : `<p class="muted">No documents uploaded yet.</p>`;
}

async function uploadKyc() {
  const docType = document.getElementById("kyc-type").value;
  const file = document.getElementById("kyc-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  await Api.postForm("/customers/me/documents", form);
  loadKycList();
}

async function renderProducts() {
  const app = document.getElementById("app");
  const products = await Api.get("/products");

  app.innerHTML = `
    ${nav("products")}
    <div class="page">
      <h1>Product Catalog</h1>
      <p class="muted">Placeholder catalog for this project.</p>
      <div class="grid-2">
        ${products
          .map(
            (p) => `
          <div class="card">
            <div style="display:flex; justify-content:space-between;">
              <strong>${p.name}</strong>
              <span class="badge badge-status">${p.category}</span>
            </div>
            <p class="muted">${p.description || ""}</p>
            <p class="muted">Waiting period: ${p.waiting_period_days} days</p>
            <button class="btn-primary" onclick="purchaseProduct('${p.id}')">Buy this policy</button>
          </div>`
          )
          .join("")}
      </div>
    </div>
  `;
}

async function purchaseProduct(productId) {
  const sumInsured = prompt("Sum insured amount:", "500000");
  if (!sumInsured) return;
  try {
    await Api.post(`/products/${productId}/purchase`, { sum_insured: parseFloat(sumInsured) });
    alert("Policy purchased! Check My Policies.");
    location.hash = "#/policies";
  } catch (e) {
    alert(e.message);
  }
}

async function renderPolicies() {
  const app = document.getElementById("app");
  const policies = await Api.get("/customers/me/policies");
  app.innerHTML = `
    ${nav("policies")}
    <div class="page">
      <h1>My Policies</h1>
      ${
        policies.length
          ? policies
              .map(
                (p) => `
        <div class="card">
          <div style="display:flex; justify-content:space-between;">
            <strong>Policy ${p.id.slice(0, 8)}…</strong>
            <span class="badge badge-success">${p.status}</span>
          </div>
          <p class="muted">Sum insured: ${p.sum_insured} · Premium: ${p.premium_amount}/yr</p>
          <p class="muted">${p.start_date} → ${p.end_date} · Next due: ${p.next_due_date || "—"}</p>
        </div>`
              )
              .join("")
          : `<p class="muted">No policies yet — visit Products to purchase one.</p>`
      }
    </div>
  `;
}

async function renderNotifications() {
  const app = document.getElementById("app");
  const notifications = await Api.get("/notifications");
  app.innerHTML = `
    ${nav("notifications")}
    <div class="page" style="max-width:700px;">
      <h1>Notifications</h1>
      ${
        notifications.length
          ? notifications
              .map(
                (n) => `
        <div class="card" style="${n.is_read ? "opacity:0.6;" : ""}">
          <div class="muted" style="text-transform:uppercase; font-size:0.75rem;">${n.type}</div>
          <p>${n.content}</p>
        </div>`
              )
              .join("")
          : `<p class="muted">No notifications yet.</p>`
      }
    </div>
  `;
}
