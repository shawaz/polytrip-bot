"use client";
import { useEffect, useState } from "react";
import { api, BotConfig } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [form, setForm] = useState<Record<string, string | number>>({});
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<string | null>(null);

  useEffect(() => {
    api.getConfig().then((c) => {
      setConfig(c);
      setForm({
        risk_per_trade_usd: c.risk_per_trade_usd,
        confidence_threshold: c.confidence_threshold,
        default_strategy: c.default_strategy,
        telegram_bot_token: "",
        telegram_chat_id: "",
        polymarket_api_key: "",
        polymarket_api_secret: "",
        polymarket_private_key: "",
      });
    });
  }, []);

  const handleSave = async () => {
    setError(null);
    setSaved(false);
    // Only send non-empty values
    const payload = Object.fromEntries(
      Object.entries(form).filter(([, v]) => v !== "" && v !== undefined)
    );
    try {
      await api.updateConfig(payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    setTrainResult(null);
    try {
      const result = await api.trainPredictor(30) as Record<string, unknown>;
      setTrainResult(
        `Trained! CV accuracy: ${((result.cv_accuracy_mean as number) * 100).toFixed(1)}% ± ${((result.cv_accuracy_std as number) * 100).toFixed(1)}% (${result.training_samples} samples)`
      );
    } catch (e) {
      setTrainResult(e instanceof Error ? e.message : "Training failed");
    } finally {
      setTraining(false);
    }
  };

  const field = (
    key: string,
    label: string,
    type: string = "text",
    placeholder?: string
  ) => (
    <div key={key}>
      <label className="text-xs text-gray-400 block mb-1">{label}</label>
      <input
        type={type}
        value={form[key] as string ?? ""}
        onChange={(e) =>
          setForm((f) => ({ ...f, [key]: type === "number" ? parseFloat(e.target.value) : e.target.value }))
        }
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600"
      />
    </div>
  );

  if (!config) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Status badges */}
      <div className="flex gap-3 flex-wrap">
        <span className={`text-xs px-2 py-1 rounded-full ${config.polymarket_configured ? "bg-green-900 text-green-300" : "bg-gray-800 text-gray-400"}`}>
          {config.polymarket_configured ? "✓ Polymarket connected" : "✗ Polymarket not configured"}
        </span>
        <span className={`text-xs px-2 py-1 rounded-full ${config.telegram_configured ? "bg-green-900 text-green-300" : "bg-gray-800 text-gray-400"}`}>
          {config.telegram_configured ? "✓ Telegram connected" : "✗ Telegram not configured"}
        </span>
        <span className={`text-xs px-2 py-1 rounded-full ${config.ml_model_trained ? "bg-green-900 text-green-300" : "bg-yellow-900 text-yellow-300"}`}>
          {config.ml_model_trained ? "✓ ML model trained" : "⚠ ML model not trained"}
        </span>
      </div>

      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
        <h2 className="font-semibold text-sm text-gray-300">Bot Settings</h2>
        <div className="grid grid-cols-2 gap-4">
          {field("risk_per_trade_usd", "Risk Per Trade ($)", "number")}
          {field("confidence_threshold", "Confidence Threshold (0–1)", "number")}
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Default Strategy</label>
          <select
            value={form["default_strategy"] as string}
            onChange={(e) => setForm((f) => ({ ...f, default_strategy: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200"
          >
            <option value="both">Both (Ensemble)</option>
            <option value="tech">Technical Only</option>
            <option value="ml">ML Only</option>
          </select>
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
        <h2 className="font-semibold text-sm text-gray-300">Polymarket API</h2>
        {field("polymarket_api_key", "API Key", "text", "Leave blank to keep existing")}
        {field("polymarket_api_secret", "API Secret", "password", "Leave blank to keep existing")}
        {field("polymarket_private_key", "Private Key (0x...)", "password", "Leave blank to keep existing")}
      </div>

      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
        <h2 className="font-semibold text-sm text-gray-300">Telegram</h2>
        {field("telegram_bot_token", "Bot Token", "text", "Leave blank to keep existing")}
        {field("telegram_chat_id", "Chat ID", "text", "Your Telegram user/group ID")}
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          className="bg-blue-700 hover:bg-blue-600 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          Save Settings
        </button>
        {saved && <span className="text-green-400 text-sm self-center">Saved!</span>}
        {error && <span className="text-red-400 text-sm self-center">{error}</span>}
      </div>

      {/* ML Training */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-3">
        <h2 className="font-semibold text-sm text-gray-300">ML Model</h2>
        <p className="text-xs text-gray-400">
          Train the ML predictor on the last 30 days of BTC 1-min data. Required before using ML or Ensemble strategy.
        </p>
        <button
          onClick={handleTrain}
          disabled={training}
          className="bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          {training ? "Training..." : "Train ML Model"}
        </button>
        {trainResult && <p className="text-xs text-gray-300">{trainResult}</p>}
      </div>
    </div>
  );
}
