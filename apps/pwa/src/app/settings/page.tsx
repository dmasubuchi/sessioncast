"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";


export interface EventSettings {
  eventName: string;
  eventId: string;
  seriesId: string;
}

export function loadSettings(): EventSettings | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("sessioncast:event");
  return raw ? (JSON.parse(raw) as EventSettings) : null;
}

export function saveSettings(s: EventSettings) {
  localStorage.setItem("sessioncast:event", JSON.stringify(s));
}

export default function SettingsPage() {
  const router = useRouter();
  const [eventName, setEventName] = useState("");
  const [seriesId, setSeriesId] = useState("google-radio");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const s = loadSettings();
    if (s) {
      setEventName(s.eventName);
      setSeriesId(s.seriesId);
    }
  }, []);

  const handleSave = () => {
    const eventId = eventName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    saveSettings({ eventName, eventId, seriesId });
    setSaved(true);
    setTimeout(() => router.push("/"), 800);
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
      <h1 className="text-xl font-bold">イベント設定</h1>
      <p className="text-sm text-gray-500">
        カンファレンスごとに1回だけ設定します。
      </p>

      <div className="space-y-1">
        <label className="text-sm font-medium">イベント名</label>
        <input
          type="text"
          value={eventName}
          onChange={(e) => setEventName(e.target.value)}
          placeholder="例: Google Cloud Next '27"
          className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
        />
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium">ラジオシリーズID</label>
        <input
          type="text"
          value={seriesId}
          onChange={(e) => setSeriesId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
          placeholder="例: google-radio"
          className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-400 focus:outline-none"
        />
        <p className="text-xs text-gray-400">小文字・数字・ハイフンのみ使用できます</p>
      </div>

      <button
        onClick={handleSave}
        disabled={!eventName.trim()}
        className="w-full bg-blue-600 text-white rounded-lg py-3 font-semibold text-sm disabled:opacity-40"
      >
        {saved ? "保存しました ✓" : "保存して今日のページへ"}
      </button>
    </div>
  );
}
