"use client";
import { useEffect, useState, useCallback } from "react";
import { api, BotStatus, Trade } from "@/lib/api";
import { StatusCard } from "@/components/StatusCard";
import { BotControls } from "@/components/BotControls";
import { TradesTable } from "@/components/TradesTable";

export default function Dashboard() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([
        api.getStatus(),
        api.listTrades(20),
      ]);
      setStatus(s);
      setTrades(t.trades);
    } catch {
      // silently retry on next interval
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {loading ? (
        <p className="text-gray-500">Connecting to backend...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatusCard status={status} />
          <BotControls
            running={status?.running ?? false}
            onStatusChange={refresh}
          />
        </div>
      )}

      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h2 className="font-semibold text-sm text-gray-300 mb-4">Recent Trades</h2>
        <TradesTable trades={trades} />
      </div>
    </div>
  );
}
