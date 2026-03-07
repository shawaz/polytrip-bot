"use client";
import type { Trade } from "@/lib/api";

export function TradesTable({ trades }: { trades: Trade[] }) {
  if (!trades.length) {
    return <p className="text-gray-500 text-sm">No trades yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800">
            <th className="pb-2 pr-4">Time</th>
            <th className="pb-2 pr-4">Direction</th>
            <th className="pb-2 pr-4">Size</th>
            <th className="pb-2 pr-4">Entry</th>
            <th className="pb-2 pr-4">Exit</th>
            <th className="pb-2 pr-4">P&L</th>
            <th className="pb-2 pr-4">Strategy</th>
            <th className="pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
              <td className="py-2 pr-4 text-gray-400 text-xs">
                {new Date(t.timestamp).toLocaleString()}
              </td>
              <td className="py-2 pr-4">
                <span
                  className={`font-semibold ${t.direction === "YES" ? "text-green-400" : "text-red-400"}`}
                >
                  {t.direction === "YES" ? "▲ UP" : "▼ DOWN"}
                </span>
              </td>
              <td className="py-2 pr-4">${t.size_usd.toFixed(2)}</td>
              <td className="py-2 pr-4">{t.entry_price?.toFixed(4) ?? "—"}</td>
              <td className="py-2 pr-4">{t.exit_price?.toFixed(4) ?? "—"}</td>
              <td className="py-2 pr-4">
                {t.pnl != null ? (
                  <span className={t.pnl >= 0 ? "text-green-400" : "text-red-400"}>
                    {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td className="py-2 pr-4 text-gray-400 capitalize">{t.strategy}</td>
              <td className="py-2">
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    t.status === "open"
                      ? "bg-blue-900 text-blue-300"
                      : t.status === "closed"
                      ? "bg-gray-800 text-gray-400"
                      : "bg-yellow-900 text-yellow-300"
                  }`}
                >
                  {t.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
