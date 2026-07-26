const State = {
  getToken() {
    return localStorage.getItem("insuramind_token");
  },
  setToken(token) {
    localStorage.setItem("insuramind_token", token);
  },
  clearToken() {
    localStorage.removeItem("insuramind_token");
  },
  getRole() {
    return localStorage.getItem("insuramind_role");
  },
  setRole(role) {
    localStorage.setItem("insuramind_role", role);
  },
  clearRole() {
    localStorage.removeItem("insuramind_role");
  },
  isLoggedIn() {
    return !!this.getToken();
  },
  logout() {
    const role = this.getRole();
    this.clearToken();
    this.clearRole();
    if (role === "agent" || role === "admin") {
      window.location.href = "../agent/index.html";
    } else if (role === "customer") {
      window.location.href = "../customer/index.html";
    } else {
      window.location.href = "../index.html";
    }
  },
};
