"use client";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import type { Trade } from "@/lib/api";

interface Props {
  trades: Trade[];
}

export function PnlChart({ trades }: Props) {
  // Build cumulative P&L from closed trades, oldest first
  const closed = [...trades]
    .filter((t) => t.status === "closed" && t.pnl !== null)
    .reverse();

  if (closed.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-600 text-sm">
        No closed trades yet
      </div>
    );
  }

  let cumulative = 0;
  const data = closed.map((t) => {
    cumulative += t.pnl!;
    return {
      label: new Date(t.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      pnl: parseFloat(cumulative.toFixed(2)),
    };
  });

  const isPositive = data[data.length - 1].pnl >= 0;
  const color = isPositive ? "#4ade80" : "#f87171"; // green-400 / red-400

  return (
    <ResponsiveContainer width="100%" height={120}>
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="label" hide />
        <YAxis hide domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", fontSize: 12 }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, "Cumulative P&L"]}
        />
        <ReferenceLine y={0} stroke="#374151" strokeDasharray="3 3" />
        <Area
          type="monotone"
          dataKey="pnl"
          stroke={color}
          strokeWidth={2}
          fill="url(#pnlGrad)"
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
