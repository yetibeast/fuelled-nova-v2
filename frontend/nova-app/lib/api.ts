// API fetch wrappers — all requests go through Next.js rewrite proxy to FastAPI :8100

export async function fetchHealth() {
  const res = await fetch("/api/health");
  return res.json();
}

export async function fetchRecentValuations() {
  const res = await fetch("/api/valuations/recent");
  return res.json();
}

export async function fetchMarketCategories() {
  const res = await fetch("/api/market/categories");
  return res.json();
}

export async function fetchMarketSources() {
  const res = await fetch("/api/market/sources");
  return res.json();
}

export async function fetchMarketOpportunities() {
  const res = await fetch("/api/market/opportunities");
  return res.json();
}

export async function fetchMarketRepricing() {
  const res = await fetch("/api/market/repricing");
  return res.json();
}

export async function fetchRiskRules() {
  const res = await fetch("/api/methodology/risk-rules");
  return res.json();
}

export async function fetchFeedback(rating?: string) {
  const url = rating && rating !== "all"
    ? `/api/feedback/recent?rating=${rating}`
    : "/api/feedback/recent";
  const res = await fetch(url);
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function sendPriceQuery(formData: FormData) {
  const res = await fetch("/api/price", { method: "POST", body: formData });
  return res.json();
}

export async function generateReport(formData: FormData) {
  const res = await fetch("/api/report", { method: "POST", body: formData });
  if (!res.ok) throw new Error("Report generation failed");
  return res.blob();
}
