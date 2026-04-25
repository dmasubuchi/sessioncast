"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { collection, query, where, orderBy, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { createSession, type SessionNote } from "@/lib/firestore";
import { loadSettings, type EventSettings } from "./settings/page";

interface SessionWithId extends SessionNote {
  id: string;
}

export default function TodayPage() {
  const [settings, setSettings] = useState<EventSettings | null>(null);
  const [sessions, setSessions] = useState<SessionWithId[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  useEffect(() => {
    if (!settings?.eventId) return;
    const q = query(
      collection(db, "sessions"),
      where("eventId", "==", settings.eventId),
      orderBy("createdAt", "desc")
    );
    return onSnapshot(q, (snap) => {
      setSessions(snap.docs.map((d) => ({ id: d.id, ...(d.data() as SessionNote) })));
    });
  }, [settings?.eventId]);

  const handleAddNote = async () => {
    if (!title.trim() || !settings) return;
    setSaving(true);
    await createSession({
      title: title.trim(),
      notes,
      eventId: settings.eventId,
      tags: [],
    });
    setTitle("");
    setNotes("");
    setShowForm(false);
    setSaving(false);
  };

  if (!settings) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center space-y-4">
        <p className="text-2xl">👋</p>
        <p className="font-semibold">はじめに、今のイベントを設定してください</p>
        <Link href="/settings" className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium text-sm">
          イベントを設定する →
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold leading-tight">{settings.eventName}</h1>
          <p className="text-xs text-gray-400">{settings.seriesId}</p>
        </div>
        <Link href="/settings" className="text-xs text-gray-400 border rounded px-2 py-1">
          変更
        </Link>
      </div>

      {/* Quick add */}
      {!showForm ? (
        <div className="flex gap-2">
          <button
            onClick={() => { setShowForm(true); setTimeout(() => textareaRef.current?.focus(), 50); }}
            className="flex-1 flex items-center gap-2 border-2 border-dashed border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-400 hover:border-blue-300 hover:text-blue-500 transition-colors"
          >
            <span className="text-lg">✏️</span>
            メモを追加
          </button>
          <Link
            href="/upload"
            className="flex items-center gap-2 border-2 border-dashed border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-400 hover:border-blue-300 hover:text-blue-500 transition-colors"
          >
            <span className="text-lg">📷</span>
          </Link>
        </div>
      ) : (
        <div className="border rounded-xl p-4 space-y-3 shadow-sm">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="セッションタイトル"
            className="w-full text-sm font-medium border-b pb-2 focus:outline-none focus:border-blue-400"
          />
          <textarea
            ref={textareaRef}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="メモ、キーワード、気になったこと…"
            rows={5}
            className="w-full text-sm font-mono resize-none focus:outline-none"
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => { setShowForm(false); setTitle(""); setNotes(""); }}
              className="text-sm text-gray-400 px-3 py-1"
            >
              キャンセル
            </button>
            <button
              onClick={handleAddNote}
              disabled={saving || !title.trim()}
              className="text-sm bg-blue-600 text-white px-4 py-1.5 rounded-lg disabled:opacity-40"
            >
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </div>
      )}

      {/* Sessions list */}
      {sessions.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">
          まだメモがありません。セッション中にどんどん追加してください。
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">{sessions.length}件のメモ</p>
          {sessions.map((s) => (
            <div key={s.id} className="border rounded-xl p-3 space-y-1">
              <p className="text-sm font-medium">{s.title}</p>
              {s.notes && (
                <p className="text-xs text-gray-500 line-clamp-2">{s.notes}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Review CTA */}
      {sessions.length >= 2 && (
        <Link
          href="/review"
          className="block w-full text-center bg-indigo-600 text-white py-3 rounded-xl font-medium text-sm"
        >
          AIにまとめを確認してもらう →
        </Link>
      )}
    </div>
  );
}
