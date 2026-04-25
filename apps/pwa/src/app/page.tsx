"use client";

import { useState } from "react";
import Link from "next/link";
import { createSession, createEpisode } from "@/lib/firestore";

const SERIES_OPTIONS = [
  { id: "google-radio",          label: "Google Radio" },
  { id: "anthropic-radio",       label: "Anthropic Radio" },
  { id: "hippo-radio",           label: "Hippo Radio" },
];

export default function Home() {
  const [title, setTitle]   = useState("");
  const [notes, setNotes]   = useState("");
  const [seriesId, setSeries] = useState("google-radio");
  const [loading, setLoading] = useState(false);
  const [episodeId, setEpisodeId] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !notes) return;
    setLoading(true);

    const sessionId = await createSession({
      title,
      notes,
      eventId: "manual",
      tags: [],
    });

    const id = await createEpisode({
      sessionId,
      seriesId,
      status: "pending",
    });

    setEpisodeId(id);
    setLoading(false);
    setTitle("");
    setNotes("");
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">SessionCast</h1>
        <Link href="/episodes" className="text-sm text-blue-600 underline">
          エピソード一覧 →
        </Link>
      </div>

      <p className="text-gray-500 mb-6 text-sm">
        セッションのメモを入力すると、AIがラジオ台本・ブログ・動画を自動生成します。
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium mb-1">セッションタイトル</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例: Agent Context Engineering for Production"
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">シリーズ</label>
          <select
            value={seriesId}
            onChange={(e) => setSeries(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {SERIES_OPTIONS.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">メモ</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={10}
            placeholder="セッションで聞いたこと、気になったキーワード、引用など何でも..."
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white rounded-lg py-3 font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "送信中..." : "生成開始 →"}
        </button>
      </form>

      {episodeId && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg text-sm">
          エピソードを登録しました。
          <Link href="/episodes" className="ml-2 text-blue-600 underline">
            進捗を確認 →
          </Link>
        </div>
      )}
    </main>
  );
}
