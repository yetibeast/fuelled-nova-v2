// API fetch wrappers — all requests go through Next.js rewrite proxy to FastAPI :8100

/* ---------- Auth helpers ---------- */

export interface NovaUser {
  id: string;
  name: string;
  email: string;
  role: string;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("nova_token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function getStoredUser(): NovaUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("nova_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function login(email: string, password: string): Promise<{ token: string; user: NovaUser }> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(body.detail || "Login failed");
  }
  const data = await res.json();
  localStorage.setItem("nova_token", data.token);
  localStorage.setItem("nova_user", JSON.stringify(data.user));
  return data;
}

export async function verifyAuth(): Promise<NovaUser | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      localStorage.removeItem("nova_token");
      localStorage.removeItem("nova_user");
      return null;
    }
    const user = await res.json();
    localStorage.setItem("nova_user", JSON.stringify(user));
    return user;
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem("nova_token");
  localStorage.removeItem("nova_user");
}

/* ---------- Data fetchers ---------- */

export async function fetchHealth() {
  const res = await fetch("/api/health");
  return res.json();
}

export async function fetchRecentValuations() {
  const res = await fetch("/api/valuations/recent", { headers: authHeaders() });
  return res.json();
}

export async function fetchMarketCategories() {
  const res = await fetch("/api/market/categories", { headers: authHeaders() });
  return res.json();
}

export async function fetchMarketSources() {
  const res = await fetch("/api/market/sources", { headers: authHeaders() });
  return res.json();
}

export async function fetchMarketOpportunities() {
  const res = await fetch("/api/market/opportunities", { headers: authHeaders() });
  return res.json();
}

export async function fetchMarketRepricing() {
  const res = await fetch("/api/market/repricing", { headers: authHeaders() });
  return res.json();
}

export async function fetchRiskRules() {
  const res = await fetch("/api/methodology/risk-rules", { headers: authHeaders() });
  return res.json();
}

export async function fetchFeedback(rating?: string) {
  const url = rating && rating !== "all"
    ? `/api/feedback/recent?rating=${rating}`
    : "/api/feedback/recent";
  const res = await fetch(url, { headers: authHeaders() });
  return res.json();
}

export async function submitFeedback(data: {
  rating: string;
  comment?: string;
  conversation_id: string;
  message_index: number;
  user_message: string;
  structured_data: Record<string, unknown>;
  response_text: string;
}) {
  return fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
}

export async function sendPriceQuery(formData: FormData) {
  const res = await fetch("/api/price", {
    method: "POST",
    body: formData,
    headers: authHeaders(),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.text();
      if (body) detail += `: ${body}`;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export async function generateReport(formData: FormData) {
  const res = await fetch("/api/report", {
    method: "POST",
    body: formData,
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Report generation failed");
  return res.blob();
}

/* ---------- Admin: Scrapers ---------- */

async function adminGet(path: string) {
  const res = await fetch(path, { headers: authHeaders() });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function fetchScrapers() { return adminGet("/api/admin/scrapers"); }

/* ---------- Admin: AI ---------- */

export function fetchAIPrompt() { return adminGet("/api/admin/ai/prompt"); }
export function fetchAIUsage() { return adminGet("/api/admin/ai/usage"); }
export function fetchAITools() { return adminGet("/api/admin/ai/tools"); }

/* ---------- Admin: Users ---------- */

export function fetchUsers() { return adminGet("/api/admin/users"); }

export async function createUser(data: { name: string; email: string; role: string; password: string }) {
  const res = await fetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Failed to create user" }));
    throw new Error(body.detail || "Failed to create user");
  }
  return res.json();
}

export async function updateUser(id: string, data: { role?: string; status?: string }) {
  const res = await fetch(`/api/admin/users/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Failed to update user" }));
    throw new Error(body.detail || "Failed to update user");
  }
  return res.json();
}

/* ---------- Admin: Logs ---------- */

export function fetchAdminValuations() { return adminGet("/api/admin/valuations"); }

export function fetchAdminFeedback(negativeOnly = false) {
  return adminGet(negativeOnly ? "/api/admin/feedback?negative_only=true" : "/api/admin/feedback");
}

/* ---------- Gold Tables ---------- */

export function fetchGoldRcn() { return adminGet("/api/admin/gold/rcn"); }
export function fetchGoldMarket() { return adminGet("/api/admin/gold/market"); }
export function fetchGoldDepreciation() { return adminGet("/api/admin/gold/depreciation"); }
export function fetchGoldGaps() { return adminGet("/api/admin/gold/gaps"); }

export async function updateGoldRcn(id: string, data: Record<string, unknown>) {
  const res = await fetch(`/api/admin/gold/rcn/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Update failed: ${res.status}`);
  return res.json();
}

export async function deleteGoldRcn(id: string) {
  const res = await fetch(`/api/admin/gold/rcn/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
  return res.json();
}

/* ---------- Competitive ---------- */

export function fetchCompetitiveSummary() { return adminGet("/api/competitive/summary"); }

/* ---------- Batch Pricing ---------- */

export async function uploadBatchSpreadsheet(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/price/batch/upload", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(body.detail || "Upload failed");
  }
  return res.json();
}

export async function exportBatchSpreadsheet(results: unknown[]) {
  const res = await fetch("/api/price/batch/export", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ results }),
  });
  if (!res.ok) throw new Error("Export failed");
  return res.blob();
}

export async function exportBatchReport(results: unknown[], summary?: Record<string, unknown>) {
  const res = await fetch("/api/price/batch/report", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ results, summary: summary || {} }),
  });
  if (!res.ok) throw new Error("Report generation failed");
  return res.blob();
}

/* ---------- AI Daily Usage ---------- */

export function fetchDailyUsage() { return adminGet("/api/admin/ai/daily-usage"); }
export function fetchRecentPricing() { return adminGet("/api/admin/ai/recent"); }
