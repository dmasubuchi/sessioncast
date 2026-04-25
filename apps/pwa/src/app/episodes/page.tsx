"use client";

import { useEffect, useState } from "react";
import {
  collection,
  query,
  orderBy,
  onSnapshot,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import type { Episode, PipelineStatus } from "@/lib/firestore";

const STATUS_COLORS: Record<PipelineStatus, string> = {
  pending:     "bg-gray-200 text-gray-700",
  researching: "bg-blue-100 text-blue-700",
  writing:     "bg-yellow-100 text-yellow-700",
  tts:         "bg-purple-100 text-purple-700",
  rendering:   "bg-orange-100 text-orange-700",
  publishing:  "bg-cyan-100 text-cyan-700",
  done:        "bg-green-100 text-green-700",
  error:       "bg-red-100 text-red-700",
};

const STATUS_LABEL: Record<PipelineStatus, string> = {
  pending:     "待機中",
  researching: "調査中",
  writing:     "執筆中",
  tts:         "音声生成",
  rendering:   "動画生成",
  publishing:  "公開中",
  done:        "完了",
  error:       "エラー",
};

type EpisodeWithId = Episode & { id: string };

export default function EpisodesPage() {
  const [episodes, setEpisodes] = useState<EpisodeWithId[]>([]);

  useEffect(() => {
    const q = query(collection(db, "episodes"), orderBy("createdAt", "desc"));
    return onSnapshot(q, (snap) => {
      setEpisodes(
        snap.docs.map((d) => ({ id: d.id, ...(d.data() as Episode) }))
      );
    });
  }, []);

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Episodes</h1>

      {episodes.length === 0 && (
        <p className="text-gray-500">まだエピソードがありません。セッションノートを入力して生成を開始してください。</p>
      )}

      <ul className="space-y-4">
        {episodes.map((ep) => (
          <li key={ep.id} className="border rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm text-gray-600">{ep.seriesId} / {ep.sessionId}</span>
              <span className={`text-xs px-2 py-1 rounded-full font-semibold ${STATUS_COLORS[ep.status]}`}>
                {STATUS_LABEL[ep.status]}
              </span>
            </div>

            {ep.compoundAccuracy !== undefined && (
              <div className="mt-2 text-sm text-gray-500">
                複合精度:{" "}
                <span className={ep.compoundAccuracy >= 0.9 ? "text-green-600 font-semibold" : "text-orange-500 font-semibold"}>
                  {(ep.compoundAccuracy * 100).toFixed(1)}%
                </span>
                {ep.contextTokensMax !== undefined && (
                  <span className="ml-4">
                    Context max:{" "}
                    <span className={ep.contextTokensMax > 50000 ? "text-orange-500" : "text-gray-700"}>
                      {ep.contextTokensMax.toLocaleString()} tokens
                    </span>
                  </span>
                )}
              </div>
            )}

            {ep.videoUrl && (
              <a href={ep.videoUrl} target="_blank" rel="noopener noreferrer"
                className="mt-3 inline-block text-sm text-blue-600 underline">
                動画を見る →
              </a>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
