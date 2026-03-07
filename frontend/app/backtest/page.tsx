"use client";
import { useEffect, useState } from "react";
import { api, BacktestRun } from "@/lib/api";
import { BacktestChart } from "@/components/BacktestChart";

export default function BacktestPage() {
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-03-01");
  const [strategy, setStrategy] = useState("both");
  const [capital, setCapital] = useState("1000");
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selected, setSelected] = useState<BacktestRun | null>(null);

  useEffect(() => {
    api.listBacktests().then(setRuns).catch(() => {});
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setMessage(null);
    try {
      await api.runBacktest({
        start_date: startDate,
        end_date: endDate,
        strategy,
        initial_capital: parseFloat(capital),
      });
      setMessage("Backtest started! Results will appear below when complete.");
      setTimeout(async () => {
        const updated = await api.listBacktests();
        setRuns(updated);
        setRunning(false);
      }, 5000);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed to start backtest");
      setRunning(false);
    }
  };

  const loadRun = async (run: BacktestRun) => {
    const detail = await api.getBacktest(run.id);
    setSelected(detail);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Backtest</h1>

      {/* Controls */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
        <h2 className="font-semibold text-sm text-gray-300">Run New Backtest</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
            >
              <option value="both">Both (Ensemble)</option>
              <option value="tech">Technical</option>
              <option value="ml">ML</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Capital ($)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
            />
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          {running ? "Running..." : "Run Backtest"}
        </button>
        {message && <p className="text-xs text-blue-400">{message}</p>}
      </div>

      {/* Previous runs */}
      {runs.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <h2 className="font-semibold text-sm text-gray-300 mb-3">Previous Runs</h2>
          <div className="space-y-2">
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => loadRun(r)}
                className="w-full text-left bg-gray-800 hover:bg-gray-700 rounded-lg p-3 text-sm transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-medium">{r.start_date} → {r.end_date}</span>
                    <span className="ml-2 text-xs bg-gray-700 px-1.5 py-0.5 rounded capitalize">
                      {r.strategy}
                    </span>
                  </div>
                  <span
                    className={`font-semibold ${(r.total_return_pct ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}
                  >
                    {(r.total_return_pct ?? 0) >= 0 ? "+" : ""}{r.total_return_pct?.toFixed(1)}%
                  </span>
                </div>
                <p className="text-gray-400 text-xs mt-1">
                  {r.total_trades} trades · Win rate {r.win_rate?.toFixed(1)}% · Sharpe {r.sharpe_ratio?.toFixed(2)} · Max DD {r.max_drawdown?.toFixed(1)}%
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Selected run detail */}
      {selected && (
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
          <h2 className="font-semibold text-sm text-gray-300">
            {selected.start_date} → {selected.end_date} ({selected.strategy})
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "Return", value: `${(selected.total_return_pct ?? 0) >= 0 ? "+" : ""}${selected.total_return_pct?.toFixed(1)}%`, good: (selected.total_return_pct ?? 0) >= 0 },
              { label: "Win Rate", value: `${selected.win_rate?.toFixed(1)}%`, good: (selected.win_rate ?? 0) >= 50 },
              { label: "Trades", value: String(selected.total_trades), good: true },
              { label: "Sharpe", value: selected.sharpe_ratio?.toFixed(2), good: (selected.sharpe_ratio ?? 0) >= 1 },
              { label: "Max DD", value: `${selected.max_drawdown?.toFixed(1)}%`, good: (selected.max_drawdown ?? 0) < 10 },
            ].map(({ label, value, good }) => (
              <div key={label} className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-500">{label}</p>
                <p className={`font-semibold ${good ? "text-green-400" : "text-red-400"}`}>{value}</p>
              </div>
            ))}
          </div>

          {selected.equity_curve && selected.equity_curve.length > 0 && (
            <BacktestChart data={selected.equity_curve} />
          )}

          {selected.trades && selected.trades.length > 0 && (
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-800">
                    <th className="pb-2 pr-3">Date</th>
                    <th className="pb-2 pr-3">Dir</th>
                    <th className="pb-2 pr-3">Conf</th>
                    <th className="pb-2 pr-3">Entry</th>
                    <th className="pb-2 pr-3">Exit</th>
                    <th className="pb-2">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.trades.slice(0, 50).map((t, i) => (
                    <tr key={i} className="border-b border-gray-800/40">
                      <td className="py-1 pr-3 text-gray-400">{new Date(t.date).toLocaleDateString()}</td>
                      <td className={`py-1 pr-3 ${t.direction === "YES" ? "text-green-400" : "text-red-400"}`}>
                        {t.direction === "YES" ? "▲" : "▼"} {t.direction}
                      </td>
                      <td className="py-1 pr-3">{(t.confidence * 100).toFixed(1)}%</td>
                      <td className="py-1 pr-3">{t.entry_price.toFixed(2)}</td>
                      <td className="py-1 pr-3">{t.exit_price.toFixed(2)}</td>
                      <td className={`py-1 ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {selected.trades.length > 50 && (
                <p className="text-xs text-gray-500 mt-2">Showing first 50 of {selected.trades.length} trades.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
