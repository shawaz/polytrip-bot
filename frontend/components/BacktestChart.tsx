"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface EquityPoint {
  date: string;
  value: number;
}

export function BacktestChart({ data }: { data: EquityPoint[] }) {
  if (!data.length) return null;

  const formatted = data.map((d) => ({
    ...d,
    date: new Date(d.date).toLocaleDateString(),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={formatted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickLine={false}
          interval={Math.floor(data.length / 6)}
        />
        <YAxis
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickLine={false}
          tickFormatter={(v) => `$${v.toFixed(0)}`}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#d1d5db" }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, "Equity"]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
