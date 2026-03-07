"use client";
import type { BotStatus } from "@/lib/api";

export function StatusCard({ status }: { status: BotStatus | null }) {
  if (!status) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-3">
      <div className="flex items-center gap-2">
        <span
          className={`w-2.5 h-2.5 rounded-full ${status.running ? "bg-green-400" : "bg-gray-500"}`}
        />
        <span className="font-semibold text-sm">{status.running ? "Running" : "Stopped"}</span>
        {status.running && (
          <span className="ml-2 text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full">
            {status.strategy}
          </span>
        )}
      </div>

      {status.open_trade && (
        <div className="bg-gray-800 rounded-lg p-3 text-sm space-y-1">
          <p className="text-gray-400">Open Position</p>
          <p>
            <span
              className={`font-bold ${status.open_trade.direction === "YES" ? "text-green-400" : "text-red-400"}`}
            >
              {status.open_trade.direction === "YES" ? "▲ LONG" : "▼ SHORT"}
            </span>{" "}
            ${status.open_trade.size_usd.toFixed(2)} @ {status.open_trade.entry_price?.toFixed(4)}
          </p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-gray-500 text-xs">Today P&L</p>
          <p className={`font-semibold ${status.today_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
            {status.today_pnl >= 0 ? "+" : ""}${status.today_pnl.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Total P&L</p>
          <p className={`font-semibold ${status.total_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
            {status.total_pnl >= 0 ? "+" : ""}${status.total_pnl.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Win Rate</p>
          <p className="font-semibold">{status.win_rate.toFixed(1)}%</p>
        </div>
      </div>

      {status.last_error && (
        <p className="text-xs text-red-400 bg-red-900/20 rounded p-2 truncate">
          ⚠ {status.last_error}
        </p>
      )}
    </div>
  );
}
