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
  user_email?: string;
  user_name?: string;
  trace_id?: string;
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

export function createScraper(data: { name: string; url: string; scraper_type: string; schedule_cron?: string }) {
  return fetch("/api/admin/scrapers", { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(data) }).then(r => r.json());
}
export function updateScraper(id: string, data: Record<string, unknown>) {
  return fetch(`/api/admin/scrapers/${id}`, { method: "PUT", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(data) }).then(r => r.json());
}
export function deleteScraper(id: string) {
  return fetch(`/api/admin/scrapers/${id}`, { method: "DELETE", headers: authHeaders() });
}
export function triggerScraperRun(id: string) {
  return fetch(`/api/admin/scrapers/${id}/run`, { method: "POST", headers: authHeaders() });
}
export function pauseScraper(id: string) {
  return fetch(`/api/admin/scrapers/${id}/pause`, { method: "POST", headers: authHeaders() });
}
export function resumeScraper(id: string) {
  return fetch(`/api/admin/scrapers/${id}/resume`, { method: "POST", headers: authHeaders() });
}
export function fetchScraperRuns(id: string) {
  return adminGet(`/api/admin/scrapers/${id}/runs`);
}
export function fetchRecentRuns() {
  return adminGet("/api/admin/scrapers/runs/recent");
}
export function triggerHarvest() {
  return fetch("/api/admin/scrapers/harvest", { method: "POST", headers: authHeaders() });
}
export function fetchHarvestStats() {
  return adminGet("/api/admin/scrapers/harvest/stats");
}

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

export function fetchGoldHealth() { return adminGet("/api/admin/gold/health"); }
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

/* ---------- Batch Polling ---------- */

export async function startBatchJob(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/price/batch/start", {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error("Failed to start batch job");
  return res.json();
}

export async function pollBatchStatus(jobId: string) {
  const res = await fetch(`/api/price/batch/${jobId}/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to poll batch status");
  return res.json();
}

/* ---------- Tiered Reports ---------- */

export async function generateTieredReport(tier: number, type: string, data: Record<string, unknown>): Promise<Blob> {
  const res = await fetch("/api/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ tier, type, data }),
  });
  if (!res.ok) throw new Error("Failed to generate report");
  return res.blob();
}

/* ---------- AI Daily Usage & Cost ---------- */

export function fetchDailyUsage() { return adminGet("/api/admin/ai/daily-usage"); }
export function fetchRecentPricing() { return adminGet("/api/admin/ai/recent"); }
export function fetchCostHistory() { return adminGet("/api/admin/ai/cost-history"); }
export function fetchModelBreakdown() { return adminGet("/api/admin/ai/model-breakdown"); }

/* ---------- Conversations ---------- */

export async function fetchConversations() {
  const res = await fetch("/api/conversations", { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function createConversation(title = "New conversation") {
  const res = await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchConversation(id: string) {
  const res = await fetch(`/api/conversations/${id}`, { headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

export async function addConversationMessage(convoId: string, msg: { role: string; text?: string; data?: Record<string, unknown> | null }) {
  const res = await fetch(`/api/conversations/${convoId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(msg),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function deleteConversation(id: string) {
  const res = await fetch(`/api/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return res.ok;
}

/* ---------- Evidence ---------- */

export async function captureEvidence(data: {
  user_message: string;
  structured_data: Record<string, unknown>;
  confidence: string;
  tools_used: string[];
}) {
  const res = await fetch("/api/evidence/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function flagEvidenceReview(data: {
  evidence_id: string;
  comment?: string;
  user_correction?: number;
}) {
  const res = await fetch("/api/evidence/flag-review", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) return null;
  return res.json();
}

export function fetchReviewQueue() { return adminGet("/api/admin/evidence/review-queue"); }

export async function promoteEvidence(id: string) {
  const res = await fetch(`/api/admin/evidence/promote/${id}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Promote failed");
  return res.json();
}

/* ---------- Reports ---------- */

export function fetchRecentReports() { return adminGet("/api/reports/recent"); }

export async function generateReportFromData(data: { type: string; data: unknown }) {
  const res = await fetch("/api/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Report generation failed");
  return res.blob();
}

/* ---------- Calibration ---------- */

export function fetchGoldenFixtures() { return adminGet("/api/admin/calibration/golden-fixtures"); }
export function fetchCalibrationResults() { return adminGet("/api/admin/calibration/results"); }

export async function runGoldenCalibration() {
  const res = await fetch("/api/admin/calibration/golden", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Calibration failed");
  return res.json();
}

export async function runCalibrationUpload(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/admin/calibration/run", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(body.detail || "Calibration failed");
  }
  return res.json();
}
