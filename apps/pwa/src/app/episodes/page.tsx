"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { collection, query, orderBy, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { updateEpisodeStatus, type Episode, type PipelineStatus } from "@/lib/firestore";

const STATUS_COLOR: Record<PipelineStatus, string> = {
  pending:     "bg-gray-100 text-gray-600",
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

const IN_PROGRESS: PipelineStatus[] = ["pending", "researching", "writing", "tts", "rendering", "publishing"];

type EpisodeRow = Episode & { id: string };

export default function EpisodesPage() {
  const [episodes, setEpisodes] = useState<EpisodeRow[]>([]);

  useEffect(() => {
    const q = query(collection(db, "episodes"), orderBy("createdAt", "desc"));
    return onSnapshot(q, (snap) => {
      setEpisodes(snap.docs.map((d) => ({ id: d.id, ...(d.data() as Episode) })));
    });
  }, []);

  const retry = async (id: string) => {
    await updateEpisodeStatus(id, "pending");
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-6 space-y-4">
      <h1 className="text-xl font-bold">エピソード</h1>

      {episodes.length === 0 && (
        <p className="text-sm text-gray-400 py-8 text-center">
          まだエピソードがありません。「レビュー」タブから生成を開始してください。
        </p>
      )}

      {episodes.map((ep) => (
        <div key={ep.id} className="border rounded-xl p-4 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{ep.seriesId}</p>
              <p className="text-xs text-gray-400 truncate">{ep.sessionId}</p>
            </div>
            <span className={`shrink-0 text-xs px-2 py-1 rounded-full font-semibold ${STATUS_COLOR[ep.status]}`}>
              {STATUS_LABEL[ep.status]}
            </span>
          </div>

          {/* Progress bar for in-progress */}
          {IN_PROGRESS.includes(ep.status) && (
            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-400 rounded-full animate-pulse w-1/2" />
            </div>
          )}

          {/* Accuracy */}
          {ep.compoundAccuracy !== undefined && (
            <p className="text-xs text-gray-500">
              複合精度:{" "}
              <span className={ep.compoundAccuracy >= 0.9 ? "text-green-600 font-semibold" : "text-orange-500 font-semibold"}>
                {(ep.compoundAccuracy * 100).toFixed(1)}%
              </span>
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            {ep.status === "error" && (
              <button
                onClick={() => retry(ep.id)}
                className="text-xs bg-red-50 text-red-600 border border-red-200 px-3 py-1 rounded-lg"
              >
                再試行
              </button>
            )}
            {ep.status === "done" && (
              <Link
                href={`/episodes/${ep.id}`}
                className="text-xs bg-green-50 text-green-700 border border-green-200 px-3 py-1 rounded-lg"
              >
                出力を確認 →
              </Link>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
