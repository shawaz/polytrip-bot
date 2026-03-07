const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

export interface BotStatus {
  running: boolean;
  strategy: string;
  market_id: string | null;
  open_trade: {
    id: number;
    direction: string;
    size_usd: number;
    entry_price: number;
    strategy: string;
    timestamp: string;
  } | null;
  today_pnl: number;
  total_pnl: number;
  win_rate: number;
  last_error: string | null;
}

export interface Trade {
  id: number;
  timestamp: string;
  market_id: string;
  direction: string;
  size_usd: number;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  strategy: string;
  status: string;
}

export interface BacktestRun {
  id: number;
  created_at: string;
  start_date: string;
  end_date: string;
  strategy: string;
  initial_capital: number;
  final_capital: number;
  win_rate: number;
  total_trades: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_return_pct: number;
  equity_curve?: { date: string; value: number }[];
  trades?: {
    date: string;
    direction: string;
    confidence: number;
    entry_price: number;
    exit_price: number;
    pnl: number;
    won: boolean;
  }[];
}

export interface BotConfig {
  risk_per_trade_usd: number;
  confidence_threshold: number;
  default_strategy: string;
  telegram_configured: boolean;
  polymarket_configured: boolean;
  ml_model_trained: boolean;
}

export const api = {
  getStatus: () => apiFetch<BotStatus>("/api/status"),

  startBot: (strategy?: string) =>
    apiFetch("/api/bot/start", {
      method: "POST",
      body: JSON.stringify({ strategy }),
    }),

  stopBot: () => apiFetch("/api/bot/stop", { method: "POST" }),

  runBacktest: (params: {
    start_date: string;
    end_date: string;
    strategy: string;
    initial_capital: number;
  }) =>
    apiFetch("/api/backtest", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  listBacktests: () => apiFetch<BacktestRun[]>("/api/backtests"),

  getBacktest: (id: number) => apiFetch<BacktestRun>(`/api/backtests/${id}`),

  listTrades: (limit = 20, offset = 0) =>
    apiFetch<{ total: number; trades: Trade[] }>(
      `/api/trades?limit=${limit}&offset=${offset}`
    ),

  getConfig: () => apiFetch<BotConfig>("/api/config"),

  updateConfig: (data: Partial<BotConfig> & Record<string, unknown>) =>
    apiFetch("/api/config", { method: "PUT", body: JSON.stringify(data) }),

  trainPredictor: (days = 30) =>
    apiFetch(`/api/predictor/train?days=${days}`, { method: "POST" }),
};
