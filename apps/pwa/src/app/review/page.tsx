"use client";

import { useState, useEffect, useRef } from "react";
import { collection, query, where, orderBy, getDocs } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { createEpisode } from "@/lib/firestore";
import { loadSettings } from "../settings/page";
import type { SessionNote } from "@/lib/firestore";

interface Message {
  role: "user" | "ai";
  text: string;
  streaming?: boolean;
}

interface ProposedEpisode {
  title: string;
  sessions: string[];
  notes: string;
}

export default function ReviewPage() {
  const settings = typeof window !== "undefined" ? loadSettings() : null;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [proposed, setProposed] = useState<ProposedEpisode[] | null>(null);
  const [generating, setGenerating] = useState(false);
  const [started, setStarted] = useState(false);
  const [launching, setLaunching] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL ?? "";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startReview = async () => {
    if (!settings) return;
    setStarted(true);
    setGenerating(true);

    // Load all sessions for this event
    const q = query(
      collection(db, "sessions"),
      where("eventId", "==", settings.eventId),
      orderBy("createdAt", "asc")
    );
    const snap = await getDocs(q);
    const sessions = snap.docs.map((d) => d.data() as SessionNote);

    if (sessions.length === 0) {
      setMessages([{ role: "ai", text: "まだメモがありません。「今日」タブでセッションメモを追加してください。" }]);
      setGenerating(false);
      return;
    }

    const notesPayload = sessions
      .map((s, i) => `## [${i + 1}] ${s.title}\n${s.notes}`)
      .join("\n\n");

    // Stream from agents service
    try {
      const res = await fetch(`${agentsUrl}/review-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: settings.eventName,
          series_id: settings.seriesId,
          notes: notesPayload,
        }),
      });

      if (!res.ok || !res.body) throw new Error(`${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";

      setMessages([{ role: "ai", text: "", streaming: true }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        // SSE lines: "data: {...}\n\n"
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") break;
          try {
            const parsed = JSON.parse(raw);
            if (parsed.text) {
              aiText += parsed.text;
              setMessages([{ role: "ai", text: aiText, streaming: true }]);
            }
            if (parsed.proposed) {
              setProposed(parsed.proposed as ProposedEpisode[]);
            }
          } catch {
            // non-JSON chunk, treat as raw text
            aiText += raw;
            setMessages([{ role: "ai", text: aiText, streaming: true }]);
          }
        }
      }

      setMessages([{ role: "ai", text: aiText, streaming: false }]);
    } catch (err) {
      setMessages([{
        role: "ai",
        text: `⚠️ エラーが発生しました: ${err instanceof Error ? err.message : "不明なエラー"}\n\nAgentsサービスが起動しているか確認してください。`,
      }]);
    } finally {
      setGenerating(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || generating) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setGenerating(true);

    try {
      const res = await fetch(`${agentsUrl}/review-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: settings?.eventName ?? "",
          series_id: settings?.seriesId ?? "",
          message: userMsg,
          history: messages,
        }),
      });

      if (!res.ok || !res.body) throw new Error(`${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";

      setMessages((prev) => [...prev, { role: "ai", text: "", streaming: true }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") break;
          try {
            const parsed = JSON.parse(raw);
            if (parsed.text) aiText += parsed.text;
            if (parsed.proposed) setProposed(parsed.proposed);
          } catch {
            aiText += raw;
          }
        }
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "ai", text: aiText, streaming: true },
        ]);
      }

      setMessages((prev) => [...prev.slice(0, -1), { role: "ai", text: aiText }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", text: `⚠️ ${err instanceof Error ? err.message : "エラー"}` },
      ]);
    } finally {
      setGenerating(false);
    }
  };

  const launchGeneration = async () => {
    if (!proposed || !settings) return;
    setLaunching(true);
    for (const ep of proposed) {
      const episodeId = await createEpisode({
        sessionId: ep.sessions.join(","),
        seriesId: settings.seriesId,
        status: "pending",
      });
      await fetch(`${agentsUrl}/run-episode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: ep.notes,
          series_id: settings.seriesId,
          episode_id: episodeId,
        }),
      });
    }
    setLaunching(false);
    setMessages((prev) => [
      ...prev,
      { role: "ai", text: `✅ ${proposed.length}本の生成を開始しました。「エピソード」タブで進捗を確認できます。` },
    ]);
    setProposed(null);
  };

  if (!settings) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <p className="text-sm text-gray-500">先にイベントを設定してください。</p>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto flex flex-col h-[calc(100dvh-5rem)]">
      {/* Header */}
      <div className="px-4 py-3 border-b">
        <h1 className="font-bold">レビュー & 生成</h1>
        <p className="text-xs text-gray-400">{settings.eventName}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {!started && (
          <div className="text-center py-12 space-y-3">
            <p className="text-sm text-gray-500">
              AIが今日のメモを読んで、要点と本数を提案します。
            </p>
            <button
              onClick={startReview}
              className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-medium text-sm"
            >
              AIに確認を依頼する
            </button>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {msg.text}
              {msg.streaming && <span className="inline-block w-1 h-4 bg-gray-400 ml-0.5 animate-pulse" />}
            </div>
          </div>
        ))}

        {/* Proposed episodes confirm card */}
        {proposed && (
          <div className="border-2 border-indigo-200 rounded-2xl p-4 space-y-3 bg-indigo-50">
            <p className="font-semibold text-sm text-indigo-800">提案: {proposed.length}本のエピソード</p>
            {proposed.map((ep, i) => (
              <div key={i} className="bg-white rounded-lg px-3 py-2 text-sm">
                <p className="font-medium">{i + 1}. {ep.title}</p>
              </div>
            ))}
            <button
              onClick={launchGeneration}
              disabled={launching}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-xl font-medium text-sm disabled:opacity-40"
            >
              {launching ? "生成開始中…" : "この構成で生成する →"}
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      {started && (
        <div className="px-4 py-3 border-t flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="補足や修正を入力…"
            disabled={generating}
            className="flex-1 border rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-40"
          />
          <button
            onClick={sendMessage}
            disabled={generating || !input.trim()}
            className="bg-indigo-600 text-white rounded-full w-10 h-10 flex items-center justify-center disabled:opacity-40"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
