"use client";

import { useState } from "react";

const INTEREST_PRESETS = [
  "AI agents", "Gemini", "Vertex AI", "Cloud Run", "ADK / A2A",
  "Firebase", "BigQuery", "MLOps", "Security", "Cost optimization",
];

type PlanState = "idle" | "loading" | "done" | "error";

interface RecommendedSession {
  rank: number;
  title: string;
  speaker: string;
  time: string;
  relevance_score: number;
  why: string;
  pre_notes: string;
}

interface Conflict {
  time: string;
  option_a: string;
  option_b: string;
  recommendation: string;
}

interface PlanResult {
  event_name: string;
  recommended_sessions: RecommendedSession[];
  conflicts: Conflict[];
  skip_list: string[];
}

export default function PlanPage() {
  const [eventName, setEventName] = useState("Google Cloud Next '27");
  const [sessionsText, setSessionsText] = useState("");
  const [goals, setGoals] = useState("");
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [planState, setPlanState] = useState<PlanState>("idle");
  const [result, setResult] = useState<PlanResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const toggleInterest = (tag: string) => {
    setSelectedInterests((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async () => {
    if (!sessionsText.trim()) return;
    setPlanState("loading");
    setResult(null);
    setErrorMsg("");

    try {
      const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL ?? "/api/agents";
      const res = await fetch(`${agentsUrl}/plan-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: eventName,
          sessions_text: sessionsText,
          interests: selectedInterests,
          goals,
        }),
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setResult(data.plan);
      setPlanState("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setPlanState("error");
    }
  };

  return (
    <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">事前セッション計画</h1>
      <p className="text-sm text-gray-500">
        セッション一覧をペーストすると、AI が登壇者を調査して優先スケジュールを提案します。
      </p>

      {/* Event name */}
      <div className="space-y-1">
        <label className="text-sm font-medium">イベント名</label>
        <input
          type="text"
          value={eventName}
          onChange={(e) => setEventName(e.target.value)}
          className="w-full border rounded px-3 py-2 text-sm"
        />
      </div>

      {/* Sessions text */}
      <div className="space-y-1">
        <label className="text-sm font-medium">
          セッション一覧
          <span className="text-gray-400 font-normal ml-2">（自由形式でペースト — CSV・テキスト・URLどれでも可）</span>
        </label>
        <textarea
          value={sessionsText}
          onChange={(e) => setSessionsText(e.target.value)}
          placeholder={"例:\n10:00 Keynote — Sundar Pichai\n11:00 ADK Deep Dive — Gemini Team\n13:00 Cloud Run best practices..."}
          rows={8}
          className="w-full border rounded px-3 py-2 text-sm font-mono"
        />
      </div>

      {/* Interests */}
      <div className="space-y-2">
        <label className="text-sm font-medium">興味タグ</label>
        <div className="flex flex-wrap gap-2">
          {INTEREST_PRESETS.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleInterest(tag)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                selectedInterests.includes(tag)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Goals */}
      <div className="space-y-1">
        <label className="text-sm font-medium">
          このイベントで得たいこと
        </label>
        <textarea
          value={goals}
          onChange={(e) => setGoals(e.target.value)}
          placeholder="例: ADK / A2A の実装パターンを把握したい。競合の動向を掴みたい。"
          rows={3}
          className="w-full border rounded px-3 py-2 text-sm"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={planState === "loading" || !sessionsText.trim()}
        className="w-full bg-blue-600 text-white py-3 rounded font-medium disabled:opacity-40"
      >
        {planState === "loading" ? "AI が調査中…" : "セッションを調査・計画する"}
      </button>

      {planState === "error" && (
        <p className="text-red-500 text-sm">{errorMsg}</p>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 pt-4 border-t">
          <h2 className="text-lg font-bold">推奨スケジュール — {result.event_name}</h2>

          <div className="space-y-4">
            {result.recommended_sessions.map((s) => (
              <div key={s.rank} className="border rounded p-4 space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium text-sm">{s.rank}. {s.title}</span>
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full whitespace-nowrap">
                    {Math.round(s.relevance_score * 100)}% match
                  </span>
                </div>
                <p className="text-xs text-gray-500">{s.speaker} — {s.time}</p>
                <p className="text-sm">{s.why}</p>
                {s.pre_notes && (
                  <details className="mt-1">
                    <summary className="text-xs text-blue-600 cursor-pointer">事前メモを見る</summary>
                    <p className="text-xs text-gray-600 mt-1 pl-2 border-l">{s.pre_notes}</p>
                  </details>
                )}
              </div>
            ))}
          </div>

          {result.conflicts.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-medium text-sm">時間重複</h3>
              {result.conflicts.map((c, i) => (
                <div key={i} className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
                  <p className="font-medium">{c.time}</p>
                  <p>{c.option_a} vs {c.option_b}</p>
                  <p className="text-yellow-800 mt-1">推奨: {c.recommendation}</p>
                </div>
              ))}
            </div>
          )}

          {result.skip_list.length > 0 && (
            <details>
              <summary className="text-xs text-gray-400 cursor-pointer">スキップリスト ({result.skip_list.length}件)</summary>
              <ul className="mt-2 space-y-1">
                {result.skip_list.map((s, i) => (
                  <li key={i} className="text-xs text-gray-500 pl-2 border-l">・{s}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </main>
  );
}
