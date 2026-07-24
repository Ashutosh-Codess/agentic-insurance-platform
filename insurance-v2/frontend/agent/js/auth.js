/**
 * Login screen, nav, and router for the agent portal. There is
 * deliberately no register screen -- agent/admin accounts only come from
 * the seed script.
 */
function nav(active) {
  const links = [
    ["dashboard", "Dashboard"],
    ["queue", "Claim Queue"],
  ];
  return `
    <nav>
      <div class="nav-brand">Insurance Agent Portal</div>
      <div class="nav-links">
        ${links
          .map(([href, label]) => `<a href="#/${href}" class="nav-link ${active === href ? "active" : ""}">${label}</a>`)
          .join("")}
      </div>
      <button class="btn-link" onclick="doLogout()">Log out</button>
    </nav>
  `;
}

function doLogout() {
  Api.logout();
  location.hash = "#/login";
}

function renderLogin() {
  document.getElementById("app").innerHTML = `
    <div class="center-page">
      <div class="card" style="width:320px;">
        <h1>Agent Login</h1>
        <div id="login-error" class="error-text"></div>
        <input id="login-email" type="email" placeholder="Email" />
        <input id="login-password" type="password" placeholder="Password" />
        <button class="btn-primary" style="width:100%" onclick="submitLogin()">Log in</button>
        <p class="muted" style="margin-top:1rem;">Agent accounts are provisioned by an administrator.</p>
      </div>
    </div>
  `;
}

async function submitLogin() {
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  try {
    await Api.login(email, password);
    location.hash = "#/dashboard";
  } catch (e) {
    document.getElementById("login-error").textContent = e.message;
  }
}

function router() {
  const hash = location.hash.replace("#/", "") || (Api.isLoggedIn() ? "dashboard" : "login");
  if (!Api.isLoggedIn() && hash !== "login") {
    location.hash = "#/login";
    return;
  }
  if (hash === "login") return renderLogin();
  if (hash === "dashboard") return renderDashboard();
  if (hash === "queue") return renderQueue();
  if (hash.startsWith("claims/")) return renderClaimDetail(hash.split("/")[1]);
  renderDashboard();
}
