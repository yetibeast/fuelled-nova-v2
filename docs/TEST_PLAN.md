# Nova V2 — Test Plan (Phases C + D)

Covers all features built in Phase C (Intelligence Polish) and Phase D (Automation & Scale).

---

## Prerequisites

- Backend running: `cd backend && uvicorn app.main:app --port 8100`
- Frontend running: `cd frontend/nova-app && npm run dev`
- PostgreSQL accessible with `DATABASE_URL` set
- Valid admin user in the database (role = "admin")
- Logged in via `/login` with valid credentials

---

## Phase C Tests

### C1 — Cost / LLM Spend Tracking

#### C1.1 Backend: GET /api/admin/ai/cost-history

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Returns 30-day structure | `curl -H "Authorization: Bearer $TOKEN" localhost:8100/api/admin/ai/cost-history` | JSON with `daily` (30 entries), `monthly_total`, `avg_daily`, `projected_monthly` |
| 2 | Daily entries have correct shape | Inspect `daily[0]` | Each entry has `date` (YYYY-MM-DD), `queries` (int), `cost` (float) |
| 3 | Cost math is correct | Check any entry | `cost == queries * 1.50` |
| 4 | Empty log returns zeros | Delete/rename pricing_log.jsonl, re-request | All values zero, `daily` still has 30 date entries |
| 5 | Auth required | Request without token | 401 |

#### C1.2 Backend: GET /api/admin/ai/model-breakdown

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Returns model array | `curl -H "Authorization: Bearer $TOKEN" localhost:8100/api/admin/ai/model-breakdown` | Array of `{model, queries, cost, pct}` |
| 2 | Percentages sum to ~100 | Sum all `pct` values | Total = 100.0 (or close with rounding) |
| 3 | Default model appears | Check when log has no `model` field | Falls back to `claude-sonnet-4-20250514` |

#### C1.3 Frontend: AI Management Page

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Cost Overview cards render | Navigate to `/ai-management` | See Monthly Spend, Avg Daily, Projected Monthly, Total Queries |
| 2 | Budget alert shows | Ensure projected > $500 | Red alert bar with "Budget alert" message |
| 3 | 30-day chart renders | Check Cost History section | AreaChart with teal gradient fill |
| 4 | Range toggle works | Click 7D / 14D / 30D buttons | Chart data changes to show correct range |
| 5 | Model breakdown bars | Scroll to Model Breakdown | Progress bars with model names, query counts, costs, percentages |
| 6 | Loading skeleton | Throttle network, reload page | Pulse animation placeholders show before data loads |

### C2 — Conversation Persistence

#### C2.1 Backend: Conversation CRUD

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Create conversation | `POST /api/conversations` with `{"title": "Test"}` | Returns `{id, title, created_at}` |
| 2 | List conversations | `GET /api/conversations` | Array includes the created conversation |
| 3 | Get conversation with messages | `GET /api/conversations/:id` | Returns conversation with empty `messages` array |
| 4 | Add user message | `POST /api/conversations/:id/messages` with `{"role": "user", "text": "hello"}` | Returns message with `id`, `created_at` |
| 5 | Add nova message | `POST /api/conversations/:id/messages` with `{"role": "nova", "text": "hi", "data": {"response": "hi"}}` | Returns message object |
| 6 | Get with messages | Re-fetch `GET /api/conversations/:id` | `messages` array has both messages in order |
| 7 | Title auto-update | After adding first user message | Conversation title changes to first 60 chars of user text |
| 8 | Delete conversation | `DELETE /api/conversations/:id` | 200, subsequent GET returns null/empty |
| 9 | Auth isolation | Use different user token | Cannot see other user's conversations |
| 10 | Tables auto-create | Drop conversations tables, make a request | Tables recreated automatically |

#### C2.2 Frontend: Chat Panel Persistence

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | New chat creates via API | Click "New Chat" in sidebar | Network tab shows `POST /api/conversations` |
| 2 | Messages saved to API | Send a message, check network | `POST /api/conversations/:id/messages` fires for user and nova messages |
| 3 | Reload preserves history | Send messages, reload page | Previous messages reload from API |
| 4 | Conversation switching | Switch between conversations | Messages swap correctly |
| 5 | Offline fallback | Disable network, send message | Falls back to localStorage, no crash |

### C3 — Calibration Harness

#### C3.1 Backend: Calibration API

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | List golden fixtures | `GET /api/admin/calibration/golden-fixtures` | Array of 5 fixtures with `id`, `description`, `expected_fmv_low/high`, `category` |
| 2 | Run golden calibration | `POST /api/admin/calibration/golden` | Returns `{timestamp, total: 5, passed, failed, errors, accuracy_pct, results}` |
| 3 | Result shape | Inspect each result | Has `id`, `description`, `status` (PASS/FAIL/NO_FMV/ERROR), `actual_fmv`, `confidence` |
| 4 | Results cached | `GET /api/admin/calibration/results` | Returns last run results |
| 5 | CSV upload | `POST /api/admin/calibration/run` with CSV file | Parses and runs calibration on uploaded fixtures |
| 6 | Bad CSV rejected | Upload invalid CSV | 400 with descriptive error |
| 7 | Admin only | Request with non-admin token | 403 |

#### C3.2 Frontend: Calibration Page

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Page loads | Navigate to `/calibration` | See Golden Fixtures table with 5 rows |
| 2 | Fixture data correct | Check GF-001 | Shows "2019 Ariel JGK/4..." with $380,000 – $480,000 range |
| 3 | Run golden calibration | Click "Run Golden Calibration" | Button shows "Running...", then results appear below |
| 4 | Results table | After run completes | Shows ID, Description, Status (PASS/FAIL/ERROR), Expected, Actual FMV, Confidence |
| 5 | Summary metrics | Above results table | Total, Passed, Failed, Errors, Accuracy % cards |
| 6 | CSV upload | Click "Upload CSV", select file | Runs calibration and shows results |
| 7 | Error handling | Upload bad file | Error message displays |

---

## Phase D Tests

### D1 — Evidence Flywheel

#### D1.1 Backend: Evidence Capture

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Auto-capture on pricing | Send a pricing query via `POST /api/price` | `pricing_evidence_intake` table gets new row |
| 2 | Evidence fields populated | Query the row | `source_file = "nova_v2_valuation"`, manufacturer/model/category extracted, `review_flag = "auto_capture"` |
| 3 | Manual capture | `POST /api/evidence/capture` with body | Returns `{evidence_id}` |
| 4 | Table auto-creates | Drop `pricing_evidence_intake`, make request | Table recreated |

#### D1.2 Backend: Flag Review

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Flag existing evidence | `POST /api/evidence/flag-review` with `{evidence_id, comment: "price too high"}` | `review_flag` changes to `"needs_review"` |
| 2 | Flag with correction | Include `user_correction: 250000` | `user_corrected_fmv = 250000` stored |
| 3 | Missing evidence_id | Omit evidence_id | 400 error |
| 4 | Nonexistent ID | Use fake ID | 404 error |

#### D1.3 Backend: Feedback → Evidence Integration

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Thumbs-down triggers flag | `POST /api/feedback` with `{rating: "down", evidence_id: "...", comment: "wrong"}` | Evidence row gets `review_flag = "needs_review"` |
| 2 | Thumbs-up no effect | `POST /api/feedback` with `{rating: "up", evidence_id: "..."}` | Evidence row unchanged |
| 3 | Missing evidence_id | Thumbs-down without evidence_id | Feedback saved normally, no error |

#### D1.4 Backend: Review Queue + Promote

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Review queue returns flagged | `GET /api/admin/evidence/review-queue` | Returns only rows with `review_flag = "needs_review"`, sorted by `created_at DESC` |
| 2 | Includes corrections | Flag with user_correction, then check queue | `user_corrected_fmv` field present |
| 3 | Promote evidence | `POST /api/admin/evidence/promote/:id` | Returns `{status: "promoted"}`, row `review_flag` changes to `"promoted"` |
| 4 | Promoted not in queue | Re-check review queue | Promoted item no longer appears |
| 5 | Admin only | Non-admin token on review-queue | 403 |

#### D1.5 Frontend: Feedback Tab Updates

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Review queue section | Navigate to Admin > Feedback Log | "Review Queue" section appears above feedback log (if items exist) |
| 2 | Promote button | Click "Promote to Gold" on a review item | Item disappears from queue |
| 3 | Shows corrections | Item with user_corrected_fmv | Displays correction value in teal |
| 4 | Empty queue hidden | No items in review queue | Section not rendered |

### D2 — MCP Server

#### D2.1 Server Startup

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Server starts | `cd backend && python mcp_server.py` | Starts on port 8150 without errors |
| 2 | Health check | `curl localhost:8150/mcp` | MCP protocol response (SSE or JSON) |

#### D2.2 Tool Availability

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Lists 6 tools | Connect MCP client, list tools | `tool_search_comparables`, `tool_get_category_stats`, `tool_lookup_rcn`, `tool_calculate_fmv`, `tool_check_equipment_risks`, `tool_fetch_listing` |
| 2 | search_comparables | Call with `keywords: ["ariel"]` | Returns comparable listings string |
| 3 | get_category_stats | Call with `category: "compressors"` | Returns category stats string |
| 4 | lookup_rcn | Call with `equipment_type: "compressor", manufacturer: "Ariel"` | Returns RCN lookup result |
| 5 | calculate_fmv | Call with `rcn: 500000, equipment_class: "rotating", age_years: 5` | Returns FMV range string |
| 6 | check_equipment_risks | Call with `equipment_type: "compressor", age_years: 15` | Returns risk factors |
| 7 | fetch_listing | Call with valid URL | Returns page content (or helpful error) |

#### D2.3 Claude Desktop Integration

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Config loads | Add config per docs/MCP_SETUP.md, restart Claude Desktop | "fuelled-nova" server appears in tool list |
| 2 | Tool invocation | Ask Claude to "look up RCN for an Ariel JGK/4 compressor" | Claude calls `tool_lookup_rcn` and returns result |

### D3 — Reports Page

#### D3.1 Backend: Reports API

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Recent reports (empty) | `GET /api/reports/recent` | Empty array `[]` |
| 2 | Generate single report | `POST /api/reports/generate` with `{type: "single", data: {structured: {valuation: {fmv_low: 100000, fmv_high: 200000}}, response_text: "test", user_message: "test equipment"}}` | Returns .docx binary |
| 3 | Generate portfolio | `POST /api/reports/generate` with `{type: "portfolio", data: [{structured: {...}, response: "..."}]}` | Returns .docx binary |
| 4 | Report logged | After generating, check `GET /api/reports/recent` | New entry with timestamp, type, title, items, fmv_range, status |
| 5 | Auth required | Request without token | 401 |

#### D3.2 Frontend: Reports Page

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Page loads | Navigate to `/reports` | Three sections visible |
| 2 | Template cards | Check Generate Report section | Three cards: Single Equipment, Portfolio Pricing, Market Report |
| 3 | Market disabled | Click Market Report card | Nothing happens, shows "Coming soon" |
| 4 | Template selection | Click Single then Portfolio | Ring highlight moves between cards |
| 5 | Recent reports table | After generating reports | Table shows date, type, title, items, FMV range, status, download |
| 6 | Empty state | No reports generated | "No reports generated yet" message |
| 7 | Download button | Click download on a report row | .docx file downloads |
| 8 | Scheduled section | Check bottom section | "Coming soon" with disabled button |

#### D3.3 Sidebar Navigation

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Reports link visible | Check sidebar | "Reports" with description icon under INTELLIGENCE, after Pricing Agent |
| 2 | Active state | Navigate to /reports | Reports link highlighted with primary border |

### D4 — Fetch Listing (pre-existing)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Valid URL | In pricing chat: paste a real equipment listing URL | Nova fetches and reads the listing content |
| 2 | Invalid URL | Paste `https://example.com/nonexistent` | Graceful error: "Could not fetch URL" |
| 3 | Timeout handling | Paste very slow URL | Returns helpful message within 15s |

---

## Integration / End-to-End Tests

### E2E-1: Full Valuation → Evidence → Review → Promote

| Step | Action | Verify |
|------|--------|--------|
| 1 | Log in as admin | Dashboard loads |
| 2 | Go to Pricing Agent | Chat interface loads with welcome message |
| 3 | Ask "Price a 2019 Ariel JGK/4, 800 HP, 8400 hours, condition B" | Nova returns valuation with FMV range |
| 4 | Check database | `pricing_evidence_intake` has new row with `review_flag = "auto_capture"` |
| 5 | Click thumbs-down, add comment "FMV seems high" | Feedback saved |
| 6 | Check database | Evidence row now has `review_flag = "needs_review"`, comment populated |
| 7 | Go to Admin > Feedback Log | Review Queue shows the flagged item |
| 8 | Click "Promote to Gold" | Item removed from review queue |
| 9 | Check database | Evidence row has `review_flag = "promoted"` |

### E2E-2: Conversation Persistence Across Reload

| Step | Action | Verify |
|------|--------|--------|
| 1 | Start new chat | Empty conversation |
| 2 | Send 3 messages, get 3 responses | 6 entries visible |
| 3 | Refresh the browser | All 6 entries reload from API |
| 4 | Switch to another conversation and back | Messages preserved |
| 5 | Clear localStorage | Messages still load from API |

### E2E-3: Calibration Golden Run

| Step | Action | Verify |
|------|--------|--------|
| 1 | Navigate to /calibration | 5 golden fixtures in table |
| 2 | Click "Run Golden Calibration" | Button shows running state |
| 3 | Wait for completion | Summary cards appear (Total: 5, Passed/Failed/Errors) |
| 4 | Check results table | Each fixture has status, expected range, actual FMV |
| 5 | Refresh page | Last results still shown (cached) |

### E2E-4: Report Generation

| Step | Action | Verify |
|------|--------|--------|
| 1 | Price an equipment item in Pricing Agent | Get valuation response |
| 2 | Export report from pricing page | .docx downloads |
| 3 | Navigate to /reports | Recent Reports table shows the entry |
| 4 | Click download on the entry | .docx downloads again |

### E2E-5: MCP Server → Claude Desktop

| Step | Action | Verify |
|------|--------|--------|
| 1 | Start MCP server: `python backend/mcp_server.py` | Port 8150 listening |
| 2 | Configure Claude Desktop per MCP_SETUP.md | Server connected |
| 3 | Ask Claude "Search for Ariel compressors under $500k" | Claude uses `tool_search_comparables` |
| 4 | Ask "Calculate FMV for a $600k RCN compressor, 5 years old" | Claude uses `tool_calculate_fmv` |

---

## Non-Functional Tests

| # | Area | Test | Expected |
|---|------|------|----------|
| 1 | Build | `npm run build` | Zero TypeScript errors, all 16 routes generated |
| 2 | File sizes | Check all new files | All under 500 lines |
| 3 | Auth | All admin endpoints without token | 401 |
| 4 | Auth | All admin endpoints with non-admin token | 403 |
| 5 | Error handling | Invalid JSON body to POST endpoints | 400/422, not 500 |
| 6 | CORS | Frontend fetches from different origin | Allowed by middleware |
| 7 | Loading states | Throttle network on every page | Skeleton/loading indicators visible |
| 8 | Mobile | Resize to 375px width | Sidebar collapses, pages remain usable |

---

## Test Summary

| Phase | Area | Tests |
|-------|------|-------|
| C1 | Cost Tracking | 14 |
| C2 | Conversation Persistence | 15 |
| C3 | Calibration Harness | 14 |
| D1 | Evidence Flywheel | 18 |
| D2 | MCP Server | 10 |
| D3 | Reports Page | 14 |
| D4 | Fetch Listing | 3 |
| E2E | Integration | 5 flows |
| NF | Non-functional | 8 |
| **Total** | | **~96 test cases + 5 E2E flows** |
