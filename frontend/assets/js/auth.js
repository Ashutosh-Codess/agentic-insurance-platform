function getPageConfig() {
  const body = document.body;
  const allowedRoles = (body.dataset.allowedRoles || "customer")
    .split(",")
    .map((role) => role.trim())
    .filter(Boolean);

  return {
    loginRedirect: body.dataset.loginRedirect || "pages/dashboard.html",
    registerRedirect: body.dataset.registerRedirect || "pages/dashboard.html",
    allowedRoles,
    registerEnabled: body.dataset.registerEnabled !== "false",
  };
}

async function completeLogin(email, password, redirectTarget) {
  const data = await Api.login(email, password);
  State.setToken(data.access_token);

  const me = await Api.me();
  const pageConfig = getPageConfig();
  if (pageConfig.allowedRoles.length && !pageConfig.allowedRoles.includes(me.role)) {
    State.clearToken();
    throw new Error(`This page is for ${pageConfig.allowedRoles.join(" or ")} only.`);
  }

  State.setRole(me.role);
  window.location.href = redirectTarget || pageConfig.loginRedirect;
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const errorBox = document.getElementById("auth-error");

  try {
    errorBox.textContent = "";
    const pageConfig = getPageConfig();
    await completeLogin(email, password, pageConfig.loginRedirect);
  } catch (err) {
    errorBox.textContent = err.message;
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;
  const errorBox = document.getElementById("auth-error");

  try {
    errorBox.textContent = "";
    await Api.post("/auth/register", { email, password });
    const pageConfig = getPageConfig();
    await completeLogin(email, password, pageConfig.registerRedirect);
  } catch (err) {
    errorBox.textContent = err.message;
  }
}

function fillDemoCredentials(email, password) {
  document.getElementById("login-email").value = email;
  document.getElementById("login-password").value = password;
}
