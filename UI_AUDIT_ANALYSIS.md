# FinanceAI — End-to-End UI Audit

**Date:** 2026-09-24  
**Method:** Live app (localhost:3001) + Playwright, 1440×900, both themes, scroll captures  
**Artifacts:** `ui-audit-screenshots/dark/` (27), `ui-audit-screenshots/light/` (27), `manifest.json`  
**Scope:** 14 routes × dark + light. Auth pages, marketing home, and all authenticated app shells.

---

## 1. Executive verdict

The product is **functionally rich but visually inconsistent and, in dark mode, frequently unreadable**. Light mode is the stronger baseline; dark mode looks like light-mode components force-inverted with `!important` overrides rather than designed. There is **no single design system in practice** — colors, radii, gradients, badges, and empty states change page-to-page. Trust cues (fake +% deltas on ₹0 balances, raw Axios errors) further cheapen a finance product.

**Overall scores (subjective, 1–10):**

| Dimension | Light | Dark |
|---|---|---|
| Color system / palette | 5 | 3 |
| Contrast / readability (WCAG) | 6 | **2** |
| Layout & hierarchy | 5 | 5 |
| Component consistency | 4 | 3 |
| Empty & error states | 4 | 4 |
| Perceived polish / trust | 5 | 3 |
| **Composite** | **4.8** | **3.3** |

---

## 2. Inventory — pages & screens captured

| # | Route | File | Shots (D/L) | Primary issues |
|---|---|---|---|---|
| 1 | `/login` | `Login.jsx` | 1/1 | OK base; washed secondary CTA; gradient text weak in light |
| 2 | `/signup` | `Signup.jsx` | 1/1 | Same family as login; generally acceptable |
| 3 | `/` Home | `Home.jsx` | 8/8 | 8,239px marathon; palette chaos; dark bands in light mode; invisible text blocks |
| 4 | `/dashboard` | `FinancialDashboard.jsx` | 2/2 | Fake trend %; **“Why Choose” titles invisible (dark)** |
| 5 | `/upload` | `Upload.jsx` | 1/1 | “Enable Notifications” unreadable on cyan hero (dark); dead CTA styling |
| 6 | `/transactions` | `Transactions.jsx` | 1/1 | **Full-page milky overlay kills contrast in BOTH themes** |
| 7 | `/chat` | `Chat.jsx` | 2/2 | Disabled Send washed; emoji/chrome overload; light AI bubble washed |
| 8 | `/analytics` | `Analytics.jsx` | 2/2 | Pastel cards + light text **invisible in dark**; fake deltas; huge blank charts |
| 9 | `/corrections` | `Corrections.jsx` | 2/2 | **“Teach the AI” banner white-on-white (dark)** |
| 10 | `/statements` | `Statements.jsx` | 1/1 | Empty state OK-ish; muted KPI labels weak in dark |
| 11 | `/statement/:id` | `StatementDetails.jsx` | 1/1 | Raw `Request failed with status code 404` — not a product error state |
| 12 | `/investment` | `InvestmentChat.jsx` | 2/2 | MCP badge green-on-green; Portfolio Health unreadable (light); black Market Insights island in light |
| 13 | `/observability` | `Observability.jsx` | 1/1 | Table header = blank white strip (dark); select text invisible; engineer UI with no design pass |
| 14 | `/observability/rag` | `RAGObservability.jsx` | 2/2 | Same table/select failures; “What this proves” title washed (dark) |

---

## 3. Critical findings (fix first)

### C1 — Dark mode: light-surface components with light/white text (invisible copy)
Hardcoded light gradients/surfaces are not themed; text tokens stay “dark-mode white.”

| Location | Evidence (screenshot) | Problem |
|---|---|---|
| Dashboard → “Why Choose FinanceAI?” | `dark/08-analytics-p2`, dashboard lower fold | White/mint gradient panel; headings `AI-Powered`, `Real-time Analytics`, `Chat Assistant` nearly white-on-white |
| Corrections → “Teach the AI” | `dark/09-corrections-p1` | Light lavender panel; title + body white-on-light → unreadable |
| Analytics → AI Insights rows | `dark/08-analytics-p1` | Mint/ice pastel rows; insight copy white → invisible |
| Home → Processing Status card | `dark/03-home-p6`, `dark/07-chat-p2` | Light green card; “Processing Status” + row labels washed out |
| Home → analytics demo (donut/trend) | dark home mid | White chart cards punched into dark page; “Spending by Category” / “Monthly Trend” titles white-on-white |
| Upload hero → Enable Notifications | `dark/05-upload` | Ghost button on cyan: label barely visible |
| Observability/RAG → table headers | `dark/13`, `dark/14-p2` | Header row is solid white bar with no (or invisible) labels |
| Observability → Time window select | dark shots | White select, near-white option text |
| Investment → MCP POWERED badge | `dark/12` | Green text on green gradient |
| RAG → “What this proves” | `dark/14-p1` | Title washed into panel |

**Root cause pattern:** `index.css` `.dark [class~="bg-white"] { … !important }` style hacks + inline `bg-gradient-to-br from-*` light utilities that never flip with theme. Text uses `text-white` assuming dark glass, then the surface flips light (or vice versa).

### C2 — Transactions page: global haze / overlay (both themes)
`06-transactions-p1` in **dark and light** shows the entire page under a milky gray gradient — title, chips, search, empty state all low-contrast. Looks like an unintended overlay (backdrop layer, gradient pseudo-element, or loading veil) stacked above content. **Worst single screen in the app.**

### C3 — Misleading financial chrome (trust killer)
On zero-data accounts:
- Dashboard: `₹0.00` with `↗ +12.5% vs last month`, `+8.2%`, `-3.1%`, `+15`
- Analytics: `NET BALANCE ₹0.00 +12%`, `TOTAL INCOME +8%`, etc.

Fake deltas on empty data make a finance tool feel dummy-grade. Show `—`, hide delta, or only render when prior-period data exists.

### C4 — Raw technical errors as UI
`/statement/demo-upload-1` → red `!` + **“Request failed with status code 404”** (Axios string). Needs: illustration, plain-language title (“Statement not found”), body, primary action, optional request ID.

### C5 — Dark Observability tables broken
`Pipeline stage performance` / `Recent executions` / RAG tables: white header slab, missing/unreadable column labels, body text floating on dark. Light mode tables work — dark never got a table token set.

---

## 4. Color palette analysis

### What’s actually on screen
A **rainbow of competing brand colors** with no 60-30-10 discipline:

| Hue | Used for |
|---|---|
| Cyan → blue gradients | Primary buttons, hero, Upload header |
| Indigo/purple | Save Correction, Upload Statement CTA, FAB, AI chips |
| Blue→green gradient | Dashboard welcome banner |
| Emerald/green | Investment header, success, “AI ALIVE” |
| Pink/magenta | Feature icons, policy icons, expense accents |
| Orange/amber | Transactions KPI icon, speed badges |
| Red | Expenses, errors |
| Near-black navy | Observability/RAG hero panels |
| Pastel mint/ice/lavender | Analytics KPI cards, insight rows |

**Problems:**
1. **No anchor brand color.** Cyan and purple fight as “primary” across pages.
2. **Gradient abuse.** Hero cyan, welcome blue-green, correction purple, investment green — four different “primary” treatments.
3. **Pastel KPI cards in dark** (Analytics) invert the usual dark-UI rule (dark surfaces + vivid accents). Pastels + white text = C1.
4. **Badge soup on Home:** Most Popular / Popular / New / AI / Speed / Security in six hues with no semantic map.
5. **Light mode body bg** is a pale blue-lavender wash; cards are white — acceptable, but section bands on Home drop to pure black/purple even in light mode → incoherent “theme within a theme.”

### Recommended palette direction (for approval)
- **One primary:** deep blue/cyan scale (e.g. `#0EA5E9` → `#0369A1`) for CTAs, links, focus rings.
- **One secondary/accent:** violet only for AI-special surfaces (chat, copilot), not general buttons.
- **Neutrals:** slate/zinc ramp with explicit light + dark tokens (`bg`, `surface`, `surface-2`, `border`, `text`, `text-muted`).
- **Semantics only:** success green, danger red, warning amber — small doses (chips, deltas, toasts).
- Kill per-section branded gradients except **one** hero treatment reused everywhere.

---

## 5. Contrast / visibility matrix (text failures)

| Screen | Mode | Element | Approx. issue |
|---|---|---|---|
| Transactions | D+L | Whole page under haze | Effective contrast collapsed |
| Dashboard “Why Choose” | Dark | H2 + 3 labels | White on #F0FDF4-ish gradient |
| Corrections banner | Dark | Title + paragraph | White on light lavender |
| Analytics AI Insights | Dark | 4 insight sentences | White on pastel mint/ice |
| Analytics KPI values | Dark | ₹0.00 in pastel cards | Colored text on same-hue pastel (e.g. red on pink) |
| Home Processing Status | Dark | Card title + step labels | Light green surface + light text |
| Home chart demo | Dark | Chart card titles | White on white cards |
| Upload | Dark | Enable Notifications | Ghost on cyan |
| Observability + RAG | Dark | Table column headers | White slab / missing labels |
| Observability + RAG | Dark | Time-window select value | White box, near-white text |
| Investment | Dark | MCP POWERED | Green on green |
| Investment | Light | Portfolio Health, TOTAL VALUE, View Full Portfolio | Mint-on-mint |
| Investment | Both | Send (empty input) | ~30–40% opacity look — reads as broken, not disabled |
| Chat | Both | Send Query empty state | Same washed disabled pattern |
| Home hero | Light | “Like Never Before” / “Financial Data” | Cyan→lavender gradient text on pale bg — weak AA |
| Login/Signup | Light | Gradient headline second line | Same weak gradient text |
| Nav | Both | Inactive links vs active pill | Active is outline-only; weak current-page signal |
| Statements empty | Dark | KPI labels | Gray-on-gray |
| Corrections helpers | Dark | Field help text | Very dim |

**Light mode failures are fewer** but C2 (transactions haze), investment mint-on-mint, disabled buttons, and Home’s black/purple bands in light theme remain.

---

## 6. Page-by-page notes

### 6.1 Login / Signup (`01`, `02`)
**Good:** Split layout clear; form card distinct; feature list scannable; theme toggle present.  
**Fix:**
- Unify brand name: UI says **FinanceAI**, document title says **Financial Statement Analyzer**.
- Light mode: gradient phrase “Like Never Before” too low-chroma — use solid primary or darker gradient stop.
- Feature rows: icon tiles (cyan/purple/pink) don’t match later app accents — adopt icon system from app or vice versa.
- Password rule `✓ Must be at least 8 characters` always-on — show only after interaction; color should be success semantic.
- No social login / forgot password — product gap (not pure UI, but expected on auth).

### 6.2 Home (`03`, 8 shots each theme)
**Problems:**
- **8,239px** single page: hero → stats → how it works → doc types → AI capabilities → live logs → chat pitch → security → FAQ → (more). After login this is an odd “marketing inside the app” experience. Decide: marketing home for logged-out only, or compress to ≤3 screens with in-app onboarding.
- **Palette whiplash:** cyan hero → gray how-it-works → purple security → black FAQ → white analytics widgets → black chat band. In **light mode** several bands stay black — looks broken, not bold.
- Decorative **3D emoji/illustrations** (robot, documents, bar-chart toy) clash with lucide line icons elsewhere.
- Stats `10K+ / 99.9% / <2s / 24/7` are unverified marketing numbers on an internal tool.
- FAQ accordion: fine; chevron contrast OK; increase row padding and hover affordance.
- Floating purple **FAB** overlaps content bottom-right on every scroll shot — ensure it doesn’t cover CTAs; consider hiding on Home.

### 6.3 Dashboard (`04`)
- Welcome banner blue→green: nice once, but **Upload Statement ghost button on dark gradient** is low-contrast in dark (icon+label fade).
- KPI cards: structure good (label, big number, delta, icon). **Remove fake deltas** (C3). Icon tiles (white/colored squares) OK.
- Quick Actions list: clear. Recent Transactions empty state: decent CTA.
- **Why Choose FinanceAI** panel: light surface in dark mode → C1. Either theme the panel dark or force dark text tokens on it.
- No chart/data density — fine for empty account, but reserve skeleton design consistent with Analytics.

### 6.4 Upload (`05`)
- Cyan page header + dashed dropzone: dropzone hierarchy is clear.
- **Enable Notifications** button nearly invisible on cyan (dark).
- Dropzone interior in dark is a flat gray slab — add icon+label hierarchy, drag-over state, and file-type chips with real contrast.
- Three benefit cards: icon colors (blue/purple/green) again unscoped — map to neutral + one accent.
- No progress/queue UI visible in empty state — define list + per-file progress design before implementation work.

### 6.5 Transactions (`06`) — worst screen
- Haze overlay (C2) must die first; until then no other polish matters.
- After fix: title row + Export CSV OK; summary chips (`Showing 0 of 0`, Income/Expenses) too faint.
- Search + segmented All/Income/Expense + Filters: good IA; active “All” pill is blue — align with primary token.
- Empty funnel icon: generic; use a transactions-specific empty illustration + “Upload a statement” CTA (parity with Statements page).

### 6.6 Chat (`07`)
- Teal hero with “Financial Intelligence 💎”, badges `Agentic RAG v2.0`, `Long-term Memory Enabled`, `Clear Session`, `AI ALIVE` — **badge overload**; pick status (online) + one secondary meta.
- AI message card: purple gradient border bubble — OK for AI, but footer strip `NEURAL LOGIC ENGINE V4` + all-caps trust line is **dev-facing jargon**; users don’t care — move to tooltip/docs.
- Quick prompts grid: good pattern; icon colors should follow category semantics, not random hues.
- Composer: large radius pill good; **Send disabled state looks broken** (washed purple/gray). Use solid muted button + `aria-disabled`.
- Tip line with 💡: low contrast in dark.

### 6.7 Analytics (`08`)
- “INTELLIGENCE SUITE” + teal hero + Live/Refresh: over-branded; simplify to `Analytics` + date range + refresh.
- KPI pastel cards: **worst dark-mode offenders** after Transactions. Switch to dark surface + vivid number + subtle accent bar.
- Charts empty: “No category data” / “No timeline data yet” — large blank white/dark wells; add skeleton + upload CTA inside chart.
- Daily/Weekly/Monthly toggle: white container in dark theme header area — theme the control.
- **AI Insights** pastel rows: redesign as list items on surface with left accent — not candy tiles.
- Fake `+12%` chips: remove (C3).
- Category Breakdown empty copy is fine — good sentence.

### 6.8 Corrections (`09`)
- Structure (banner → form → examples) is logical.
- Banner C1 unreadable in dark.
- Full-width purple Save button: too heavy; use standard button width/alignment with form.
- Example cards: good; in dark, card bg nearly equals page bg — raise surface elevation/border.
- Form labels/help: help text too dim in dark (bump `text-muted` token).

### 6.9 Statements (`10`)
- KPI row + big empty state: solid pattern; best empty state in the app.
- Dark: label gray too close to value; icons at low opacity nearly disappear.
- Light: clean. Keep as reference for other empties.

### 6.10 Statement Details (`11`)
- Error-only view (404): raw Axios message (C4). Design full error template with illustration, title, body, back + retry.
- No page header shell (breadcrumb “Statements / detail”) — add when data exists.

### 6.11 Investment (`12`)
- Emerald header vs app cyan/purple: third brand personality. If Groww partnership requires green, confine green to this route’s local tokens only.
- **MCP POWERED** badge unreadable (dark).
- Purple AI summary card on dark: OK-ish; on light, washes out.
- Portfolio Health (light): title + labels mint-on-mint — C1 light variant.
- Market Insights: **solid black card in light mode** — jarring island; use surface + border.
- Send button disabled: same washed pattern as Chat.
- Suggestion chips row overflows/clips (“F…” cut) — horizontal scroll affordance or wrap.
- Placeholder `₹--,--` and `+₹--.--%` look like broken data — use `—` em-dash placeholders.

### 6.12 Observability (`13`) + RAG (`14`)
- Dark navy hero panel: actually decent.
- Controls: Refresh / RAG evaluation buttons OK; **time window select broken in dark**.
- KPI strip (0, 0.00s, Not measured): readable; labels could be stronger.
- Long disclaimer paragraph: wall of text — use info callout with shorter primary line.
- **Tables: broken in dark** (C5) — header slab, missing labels; empty row text floats.
- These pages are for operators: still needs density guidelines (type scale, zebra rows, status pills) not marketing gradients.

### 6.13 Global chrome (Navbar / shell)
- **8 flat nav items** equal weight — no grouping (Workspace vs Monitor). Active state = thin outline pill, easy to miss.
- Logo `F` + `FinanceAI`: OK; **right-side avatar clipped at viewport edge** in nearly every capture — padding/overflow bug.
- Theme toggle: present on auth + navbar (good). No system-preference init (defaults dark) — respect `prefers-color-scheme` on first visit.
- Page titles in tabs all `Financial Statement Analyzer` — set per-route titles.
- Toaster hardcoded `#363636` — looks wrong on light theme.

---

## 7. Cross-cutting design system gaps

1. **No real token layer in components** — CSS vars exist in `index.css`, but JSX mixes Tailwind literals, gradients, and `var(--…)` arbitrarily; dark fixes are bolt-on `!important` rules.
2. **Tailwind `darkMode` not configured**; theming is class + vars only — fine, but then every surface must consume tokens, not `bg-white`/`from-blue-500`.
3. **Radii:** 8 / 12 / 16 / 24 / `rounded-3xl` / pill — pick 3 steps (sm/md/lg).
4. **Type:** Inter + Poppins imported; weights/sizes jump (hero 5xl vs app 3xl). Define scale: 12/14/16/18/24/30/36.
5. **Icons:** lucide everywhere except home’s 3D emoji art — one illustration policy.
6. **Motion:** framer-motion entrances delay content; ensure `prefers-reduced-motion`.
7. **Empty states:** Statements good; Transactions/Analytics/Chat should match (icon + title + body + CTA).
8. **Buttons:** primary cyan vs purple gradient vs green — one primary, one AI variant, one danger, one ghost.
9. **Accessibility:** nav needs `aria-current`; icon-only theme toggle has title (good); contrast fixes above are WCAG AA prerequisites (4.5:1 body, 3:1 large).

---

## 8. Proposed redesign principles (for your approval)

1. **Token-first theming** — define `--bg`, `--surface`, `--surface-2`, `--border`, `--text`, `--text-muted`, `--primary`, `--primary-fg`, `--accent` for light + dark; delete `!important` hacks; ban raw `bg-white` / `text-white` on themed pages.
2. **One palette** — blue/cyan primary, violet reserved for AI, neutrals slate, semantics sparingly. Kill rainbow KPI pastels in dark.
3. **Fix P0 contrast bugs** — Transactions haze, dashboard Why-Choose, corrections banner, analytics insights, obs tables, investment badges, disabled buttons.
4. **Honest finance UI** — no fake % on zeros; proper placeholders (`—`); real error templates.
5. **Compress Home** — either gate marketing to logged-out or cut to hero + 3 sections + CTA.
6. **Nav IA** — group links, stronger active state, fix avatar overflow, route titles.
7. **Component pass** — Button, Input, Card, Table, EmptyState, Badge, KPI, Select: theme-aware stories used by all 14 routes.
8. **Verify both themes** — re-run this screenshot suite as the acceptance gate (script already in capture flow).

---

## 9. Suggested implementation phases (after your approval)

| Phase | Work | Risk |
|---|---|---|
| **P0** | Transactions overlay; dark C1 invisible-text set; obs tables/select; disabled buttons; 404 template; remove fake deltas | Low — high visual win |
| **P1** | Global tokens + navbar/avatar + button/input/table primitives; retint each route to tokens | Medium — touches all pages |
| **P2** | Home compression + illustration policy; analytics/dashboard KPI redesign; investment local green tokens | Medium |
| **P3** | Polish: focus rings, reduced motion, per-route titles, toast theming, a11y pass | Low |

---

## 10. Screenshot index

```
ui-audit-screenshots/
  manifest.json
  dark/   01-login … 14-rag-observability  (27 PNGs)
  light/  01-login … 14-rag-observability  (27 PNGs)
```

Viewport 1440×900; multi-shot where `scrollHeight > 900` (Home = 8 frames).

---

**Next step:** Review this audit, mark phases/principles you approve (or adjust palette direction), then we implement code changes phase-by-phase and re-capture screenshots for side-by-side verification.
