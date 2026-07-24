/**
 * Login/register screens, the top nav, and the hash router. Screens
 * themselves (renderDashboard, renderProfile, etc.) live in dashboard.js
 * and claim.js -- this file only owns auth state and routing.
 */
function nav(active) {
  const links = [
    ["dashboard", "Dashboard"],
    ["profile", "Profile"],
    ["products", "Products & Recommendations"],
    ["policies", "My Policies"],
    ["claims", "Claims"],
    ["notifications", "Notifications"],
  ];
  return `
    <nav>
      <div class="nav-brand">Insurance Platform</div>
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
        <h1>Log in</h1>
        <div id="login-error" class="error-text"></div>
        <input id="login-email" type="email" placeholder="Email" />
        <input id="login-password" type="password" placeholder="Password" />
        <button class="btn-primary" style="width:100%" onclick="submitLogin()">Log in</button>
        <p class="muted" style="text-align:center; margin-top:1rem;">
          No account? <a href="#/register">Register</a>
        </p>
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

function renderRegister() {
  document.getElementById("app").innerHTML = `
    <div class="center-page">
      <div class="card" style="width:320px;">
        <h1>Create your account</h1>
        <div id="register-error" class="error-text"></div>
        <input id="reg-name" placeholder="Full name" />
        <input id="reg-email" type="email" placeholder="Email" />
        <input id="reg-password" type="password" placeholder="Password (min 8 chars)" />
        <button class="btn-primary" style="width:100%" onclick="submitRegister()">Register</button>
        <p class="muted" style="text-align:center; margin-top:1rem;">
          Already have an account? <a href="#/login">Log in</a>
        </p>
      </div>
    </div>
  `;
}

async function submitRegister() {
  const full_name = document.getElementById("reg-name").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;
  try {
    await Api.register(email, password, full_name);
    await Api.login(email, password);
    location.hash = "#/profile";
  } catch (e) {
    document.getElementById("register-error").textContent = e.message;
  }
}

const routes = {
  login: renderLogin,
  register: renderRegister,
  dashboard: () => renderDashboard(),
  profile: () => renderProfile(),
  products: () => renderProducts(),
  policies: () => renderPolicies(),
  claims: () => renderClaims(),
  notifications: () => renderNotifications(),
};

function router() {
  const hash = location.hash.replace("#/", "") || (Api.isLoggedIn() ? "dashboard" : "login");
  if (!Api.isLoggedIn() && !["login", "register"].includes(hash)) {
    location.hash = "#/login";
    return;
  }
  const renderFn = routes[hash] || routes.dashboard;
  renderFn();
}
