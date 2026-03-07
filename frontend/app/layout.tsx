import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PolyTrip — BTC Trading Bot",
  description: "Polymarket BTC 5-min prediction trading bot dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950">
        <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center gap-6">
          <span className="font-bold text-blue-400 text-lg">⚡ PolyTrip</span>
          <Link href="/" className="text-gray-300 hover:text-white text-sm">Dashboard</Link>
          <Link href="/backtest" className="text-gray-300 hover:text-white text-sm">Backtest</Link>
          <Link href="/settings" className="text-gray-300 hover:text-white text-sm">Settings</Link>
        </nav>
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
