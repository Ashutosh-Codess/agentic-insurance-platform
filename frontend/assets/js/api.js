// Thin wrapper around fetch. Attaches the JWT if we have one, throws a
// plain Error with the server's detail message on failure.

const API_BASE = "http://127.0.0.1:8000/api/v1";

const Api = {
  async request(path, { method = "GET", body, form = false } = {}) {
    const token = State.getToken();
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!form && body !== undefined) headers["Content-Type"] = "application/json";

    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : form ? body : JSON.stringify(body),
    });

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
  },

  get(path) {
    return this.request(path);
  },
  post(path, body) {
    return this.request(path, { method: "POST", body });
  },
  put(path, body) {
    return this.request(path, { method: "PUT", body });
  },

  me() {
    return this.get("/auth/me");
  },

  // login uses the OAuth2 password form, not JSON, since that's what
  // FastAPI's OAuth2PasswordRequestForm expects on the backend
  async login(email, password) {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const res = await fetch(`${API_BASE}/auth/login`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Incorrect email or password");
    return res.json();
  },

  // streaming copilot response - not JSON, reads the response body directly
  async askCopilot(collection, question, onChunk) {
    const token = State.getToken();
    const res = await fetch(`${API_BASE}/copilot/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ collection, question }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value));
    }
  },
};
