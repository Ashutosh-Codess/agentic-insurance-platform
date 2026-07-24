/**
 * Reusable fetch wrapper for the whole customer portal. Attaches the JWT,
 * retries once after a silent refresh on a 401, and throws a plain Error
 * with the server's `detail` so every caller can just try/catch.
 *
 * Token storage is namespaced ("customer_portal_...") so this app's
 * tokens can never collide with the agent portal's tokens even if both
 * were ever served from the same origin.
 */
const Api = (() => {
  const base = window.API_BASE_URL;
  const PREFIX = "customer_portal";

  function getTokens() {
    return {
      access: localStorage.getItem(`${PREFIX}_access_token`),
      refresh: localStorage.getItem(`${PREFIX}_refresh_token`),
    };
  }

  function setTokens({ access_token, refresh_token }) {
    if (access_token) localStorage.setItem(`${PREFIX}_access_token`, access_token);
    if (refresh_token) localStorage.setItem(`${PREFIX}_refresh_token`, refresh_token);
  }

  function clearTokens() {
    localStorage.removeItem(`${PREFIX}_access_token`);
    localStorage.removeItem(`${PREFIX}_refresh_token`);
  }

  async function refreshAccessToken() {
    const { refresh } = getTokens();
    if (!refresh) throw new Error("No refresh token available");
    const res = await fetch(`${base}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) throw new Error("Session expired -- please log in again");
    const data = await res.json();
    setTokens({ access_token: data.access_token });
    return data.access_token;
  }

  async function request(path, { method = "GET", body, isForm = false, retried = false } = {}) {
    const { access } = getTokens();
    const headers = {};
    if (access) headers["Authorization"] = `Bearer ${access}`;
    if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

    const res = await fetch(`${base}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });

    if (res.status === 401 && !retried && getTokens().refresh) {
      await refreshAccessToken();
      return request(path, { method, body, isForm, retried: true });
    }

    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      try {
        const errBody = await res.json();
        detail = errBody.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }

    if (res.status === 204) return null;
    return res.json();
  }

  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    put: (path, body) => request(path, { method: "PUT", body }),
    postForm: (path, formData) => request(path, { method: "POST", body: formData, isForm: true }),

    async login(email, password) {
      const data = await request("/auth/login", { method: "POST", body: { email, password } });
      setTokens(data);
      return data;
    },
    async register(email, password, full_name) {
      return request("/auth/register", { method: "POST", body: { email, password, full_name } });
    },
    logout() {
      const { refresh } = getTokens();
      clearTokens();
      if (refresh) {
        fetch(`${base}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        }).catch(() => {});
      }
    },
    isLoggedIn() {
      return !!getTokens().access;
    },
  };
})();
