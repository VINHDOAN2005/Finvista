# 01. FRONTEND ARCHITECTURE BIBLE
**Framework:** Next.js 14+ (App Router) + TypeScript  
**Styling:** Tailwind CSS + shadcn/ui + Radix UI  
**Charts:** Tremor + ECharts  
**Focus:** Financial data visualization, low-latency UI, SaaS monetization-ready

**Status:** TO BE CREATED — Phase 5 (Highest Priority)

---

## 1. Project Setup

```bash
cd Finvista
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend
npx shadcn@latest init
npm install @tremor/react echarts echarts-for-react @tanstack/react-query zustand next-themes axios
```

**Environment:**
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8008
NEXT_PUBLIC_WS_URL=ws://localhost:8008/api/ws
```

---

## 2. Directory Structure

```
frontend/src/
├── app/
│   ├── layout.tsx              ← Root layout: Sidebar + Header
│   ├── page.tsx                ← Redirect → /dashboard
│   ├── dashboard/page.tsx
│   ├── warrants/
│   │   ├── page.tsx            ← ⭐ CORE: CW table
│   │   └── [symbol]/page.tsx   ← CW detail + Greeks + P/L heatmap
│   ├── credit/
│   │   ├── page.tsx
│   │   └── [ticker]/page.tsx
│   ├── regime/page.tsx
│   ├── portfolio/page.tsx
│   ├── news/page.tsx
│   └── settings/
│       ├── page.tsx
│       └── billing/page.tsx    ← Phase 7 PayOS
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── ConnectionStatus.tsx  ← WebSocket dot
│   ├── warrants/
│   │   ├── CWTable.tsx
│   │   ├── CWCard.tsx            ← Mobile view
│   │   ├── CWFilterPanel.tsx
│   │   ├── GreeksTable.tsx
│   │   ├── IVHVChart.tsx
│   │   └── PLHeatmap.tsx         ← VIP feature
│   ├── credit/
│   │   ├── CreditTable.tsx
│   │   └── SystemicGraph.tsx
│   ├── regime/
│   │   ├── RegimeBadge.tsx
│   │   └── GARCHChart.tsx
│   └── ui/                       ← shadcn components
├── hooks/
│   ├── useWebSocket.ts
│   ├── useOpportunities.ts       ← TanStack Query wrapper
│   └── useAuth.ts                ← Phase 7
├── lib/
│   ├── api.ts                    ← Typed API client
│   ├── types.ts                  ← All API response interfaces
│   └── formatters.ts             ← Price, Greek, % formatters
└── store/
    └── uiStore.ts                ← Zustand: dark mode, filters, sidebar
```

---

## 3. Design System

### 3.1 Color Tokens (Financial Dark Theme — Default)

```css
:root {
  --bg-primary:    #0a0e1a;
  --bg-secondary:  #111827;
  --bg-card:       #1a2235;
  --accent-teal:   #14b8a6;   /* BUY / positive */
  --accent-amber:  #f59e0b;   /* HOLD / warning */
  --accent-red:    #ef4444;   /* SELL / distress / OVERPRICED */
  --accent-blue:   #3b82f6;   /* info / links */
  --text-primary:  #f1f5f9;
  --text-muted:    #94a3b8;
  --border:        #1e293b;
}
```

### 3.2 Typography

- **UI text:** Inter (Google Fonts)
- **Financial numbers:** JetBrains Mono — prices, Greeks, scores
- **Headings:** Inter semibold

### 3.3 Number Formatting (`lib/formatters.ts`)

```typescript
export const formatPrice = (n: number) =>
  n.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export const formatGreek = (n: number) => n.toFixed(4);
export const formatPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
export const formatIVHV = (ratio: number) => ratio.toFixed(2);
```

---

## 4. State Management

### 4.1 Server State — TanStack Query

```typescript
// hooks/useOpportunities.ts
export function useOpportunities(filters: WarrantFilters) {
  return useQuery({
    queryKey: ['opportunities', filters],
    queryFn: () => api.fetchOpportunities(filters),
    staleTime: 60_000,        // 1 min (free tier: 5 min via backend)
    refetchInterval: 60_000,  // auto-refresh
  });
}
```

**NEVER use raw `useEffect` + `fetch` for API data.**

### 4.2 Client State — Zustand

```typescript
// store/uiStore.ts
interface UIStore {
  darkMode: boolean;
  sidebarOpen: boolean;
  warrantFilters: WarrantFilters;
  setWarrantFilters: (f: WarrantFilters) => void;
}
```

### 4.3 WebSocket State

```typescript
// hooks/useWebSocket.ts
export function useWebSocket(onMessage: (payload: WsPayload) => void) {
  // Connect to NEXT_PUBLIC_WS_URL
  // Auto-reconnect after 3s on disconnect
  // Update TanStack Query cache on cw_update messages
}
```

---

## 5. API Client

```typescript
// lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('finvista_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const fetchOpportunities = (params?: WarrantFilters) =>
  api.get('/api/warrants/opportunities', { params }).then(r => r.data);

export const fetchCWDetail = (symbol: string) =>
  api.get(`/api/warrants/${symbol}/history`).then(r => r.data);

export const fetchSimulate = (symbol: string) =>
  api.get(`/api/warrants/${symbol}/simulate`).then(r => r.data);  // VIP

export const fetchCreditHealth = (ticker: string) =>
  api.get(`/api/credit-health/${ticker}`).then(r => r.data);

export const fetchMarketRegime = () =>
  api.get('/api/regime/market').then(r => r.data);

export const fetchAnalystPrompt = (ticker: string, cwSymbol?: string) =>
  api.get(`/api/analyst-prompt/${ticker}`, { params: { cw_symbol: cwSymbol } }).then(r => r.data);
```

---

## 6. Core Screens

### 6.1 Warrant Dashboard (`/warrants`) — ⭐ MOST IMPORTANT

**Desktop (≥ md): Data-dense table**

| Mã CW | CPCS | TCPH | Thị giá | +/-% | IV/HV | Delta | Theta | Score | Tín hiệu | Sparkline |
|-------|------|------|---------|------|-------|-------|-------|-------|----------|-----------|

**Features:**
- Sortable columns (click header)
- IV/HV cell color: `> 1.3` → red bg, `< 0.9` → teal bg
- Signal badge: BUY (teal) / HOLD (amber) / AVOID (red)
- Inline sparkline: Tremor AreaChart 80px wide, 7 sessions
- Filter panel (collapsible):
  - CPCS / TCPH `<Select>`
  - Delta `<Slider>` 0.1–1.0
  - Score `<Slider>` 0–100
  - Strategy: Safe / Balanced / Aggressive presets
- Virtual scroll if > 100 rows (`@tanstack/react-virtual`)

**Mobile (< md): Card view**
```tsx
<div className="block md:hidden">
  {data.map(cw => <CWCard key={cw.symbol} data={cw} />)}
</div>
<div className="hidden md:block">
  <CWTable data={data} />
</div>
```

### 6.2 CW Detail (`/warrants/[symbol]`)

Sections:
1. Header: symbol, CPCS, TCPH, last price, % change
2. Greeks table: Δ, Γ, Θ, ν, ρ (4 decimal places)
3. IV vs HV chart (ECharts, 90 days)
4. Action buttons:
   - "📋 Copy Analyst Prompt" → clipboard
   - "🔬 Deep Analysis" → POST `/api/warrants/{symbol}/deep-analysis`
5. **VIP: P/L 2D Heatmap**
   - Data: `GET /api/warrants/{symbol}/simulate`
   - X: Spot change -10% to +10% (step 2%)
   - Y: Days held 1–30
   - Color: red → white → green gradient

### 6.3 Credit Dashboard (`/credit`)

- Table: ticker, company, PD score, risk label
- Row click → `/credit/[ticker]` with systemic exposure
- Top propagators widget from `/api/systemic/propagators`

### 6.4 Regime Monitor (`/regime`)

- Large regime badge from `/api/regime/market`
- GARCH vol chart per ticker
- Ticker search → `/api/regime/{ticker}`

### 6.5 Portfolio Console (`/portfolio`)

- Equity curve (Tremor AreaChart)
- Positions table with P&L
- Buttons: Scan, Reset
- API: `/api/portfolio`, `/api/portfolio/scan`

---

## 7. Responsive Strategy

| Breakpoint | Layout |
|------------|--------|
| `< md (768px)` | Card view, collapsed sidebar (hamburger) |
| `md – lg` | Table view, sidebar visible |
| `≥ lg` | Full table + filter panel side-by-side |

Tailwind pattern:
```tsx
className="hidden md:table-cell"  // desktop only column
className="block md:hidden"       // mobile only
```

---

## 8. Real-time Updates (Sprint 5.4)

**WebSocket message types:**
```typescript
type WsPayload =
  | { type: 'cw_update'; symbol: string; price: number; greeks: Greeks }
  | { type: 'signal_alert'; symbol: string; signal: 'BUY' | 'SELL'; reason: string }
  | { type: 'regime_change'; regime: string; confidence: number };
```

**On `cw_update`:** Patch TanStack Query cache for that symbol — do NOT refetch entire table.

**On `signal_alert`:** Show toast notification (shadcn Toast).

**Connection indicator:** Green dot in Header when connected, red when disconnected.

---

## 9. Loading & Error States

```tsx
// Loading
{isLoading && <Skeleton className="h-8 w-full" />}

// Error
{isError && (
  <Toast variant="destructive">
    Không thể tải dữ liệu CW. Kiểm tra kết nối backend.
  </Toast>
)}

// Empty
{data?.length === 0 && <EmptyState message="Không có CW phù hợp bộ lọc" />}
```

**Never:** Blank white screen on API failure.

---

## 10. Subscription Gating (Phase 7)

```typescript
// middleware.ts (Phase 7)
const VIP_ROUTES = ['/warrants/[symbol]/simulate', '/settings/ai-signals'];

// Component level
{user.plan === 'vip' ? <PLHeatmap data={simulateData} /> : <UpgradeBanner feature="P/L Heatmap" />}
```

**Free tier behavior:**
- CW table: 5-minute delayed data (`?delay=300` query param on backend)
- Top 5 recommendations only
- Basic Greeks (Δ, Γ) — hide Θ, ν, ρ

---

## 11. Performance Rules

1. **React.memo** on table rows — prevent full re-render on WebSocket tick
2. **Virtual scroll** for CW table (216 rows)
3. **Code split** ECharts — dynamic import, not in main bundle
4. **ISR** for static pages: dashboard summary revalidate 60s
5. **No layout shift** — skeleton loaders match final component dimensions

---

## 12. Frontend Checklist (New Feature)

- [ ] TypeScript interfaces match API response exactly
- [ ] TanStack Query for all server data
- [ ] Loading skeleton + error toast
- [ ] Mobile responsive verified at 375px
- [ ] Financial numbers formatted consistently
- [ ] Dark mode compatible
- [ ] No `useEffect` fetch anti-pattern
- [ ] WebSocket updates don't re-render entire page

---

## 13. Deployment (Phase 8)

- **Platform:** Vercel (recommended) — `vercel deploy`
- **Env vars:** Set `NEXT_PUBLIC_API_URL=https://api.finvista.vn` in Vercel dashboard
- **Domain:** `finvista.vn` → Vercel, `api.finvista.vn` → VPS backend
