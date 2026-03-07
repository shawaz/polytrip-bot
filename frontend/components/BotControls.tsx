"use client";
import { useState } from "react";
import { api } from "@/lib/api";

type Strategy = "tech" | "ml" | "both";

export function BotControls({
  running,
  onStatusChange,
}: {
  running: boolean;
  onStatusChange: () => void;
}) {
  const [strategy, setStrategy] = useState<Strategy>("both");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = async () => {
    setLoading(true);
    setError(null);
    try {
      if (running) {
        await api.stopBot();
      } else {
        await api.startBot(strategy);
      }
      onStatusChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
      <h2 className="font-semibold text-sm text-gray-300">Bot Controls</h2>

      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-400">Strategy</label>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value as Strategy)}
          disabled={running || loading}
          className="bg-gray-800 border border-gray-700 text-sm rounded px-2 py-1 text-gray-200 disabled:opacity-50"
        >
          <option value="both">Both (Ensemble)</option>
          <option value="tech">Technical Only</option>
          <option value="ml">ML Only</option>
        </select>
      </div>

      <button
        onClick={toggle}
        disabled={loading}
        className={`w-full py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 ${
          running
            ? "bg-red-700 hover:bg-red-600 text-white"
            : "bg-green-700 hover:bg-green-600 text-white"
        }`}
      >
        {loading ? "..." : running ? "Stop Bot" : "Start Bot"}
      </button>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
