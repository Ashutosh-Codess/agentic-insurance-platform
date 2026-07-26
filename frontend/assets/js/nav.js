const Nav = {
  isAgentRole(role) {
    return role === "agent" || role === "admin";
  },

  applyPortalTheme(role) {
    if (this.isAgentRole(role)) {
      document.body.classList.add("portal-agent");
    }
  },

  loginUrl(role) {
    return this.isAgentRole(role) ? "../agent/index.html" : "../customer/index.html";
  },

  render(activePage) {
    const role = State.getRole();
    this.applyPortalTheme(role);

    const header = document.getElementById("app-header");
    if (!header) return;

    const isAgent = this.isAgentRole(role);
    const portalLabel = isAgent ? "Agent Portal" : "Customer Portal";

    let links = "";
    if (isAgent) {
      links = `
        <a href="fraud-monitor.html" class="${activePage === "queue" ? "active" : ""}">Claim Queue</a>
        <a href="copilot.html" class="${activePage === "copilot" ? "active" : ""}">Copilot</a>
      `;
    } else {
      links = `
        <a href="dashboard.html" class="${activePage === "dashboard" ? "active" : ""}">Dashboard</a>
        <a href="claims.html" class="${activePage === "claims" ? "active" : ""}">My Claims</a>
        <a href="copilot.html" class="${activePage === "copilot" ? "active" : ""}">Copilot</a>
      `;
    }

    header.innerHTML = `
      <div class="brand">
        <span>InsuraMind AI</span>
        <span class="tag">${portalLabel}</span>
      </div>
      <nav>
        ${links}
        <a href="#" onclick="State.logout(); return false;">Log out</a>
      </nav>
    `;
  },

  async guard(allowedRoles, activePage) {
    if (!State.isLoggedIn()) {
      window.location.href = "../index.html";
      return null;
    }

    let me;
    try {
      me = await Api.me();
      State.setRole(me.role);
    } catch (_) {
      State.clearToken();
      State.clearRole();
      window.location.href = "../index.html";
      return null;
    }

    if (allowedRoles.length && !allowedRoles.includes(me.role)) {
      window.location.href = this.isAgentRole(me.role)
        ? "fraud-monitor.html"
        : "dashboard.html";
      return null;
    }

    this.render(activePage);
    return me;
  },
};
