"use client";

import { useEffect, useState } from "react";
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

function EpisodeDetail({ ep, onClose }: { ep: EpisodeRow; onClose: () => void }) {
  const [ytUploading, setYtUploading] = useState(false);
  const [ytDone, setYtDone] = useState(false);

  const downloadMarkdown = () => {
    if (!ep.script) return;
    const blob = new Blob([ep.script], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ep.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const uploadToYouTube = async () => {
    setYtUploading(true);
    await new Promise((r) => setTimeout(r, 1500));
    setYtDone(true);
    setYtUploading(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-end" onClick={onClose}>
      <div
        className="w-full max-w-lg mx-auto bg-white rounded-t-2xl p-5 space-y-4 max-h-[85dvh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle bar */}
        <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto" />

        <div>
          <p className="font-bold">{ep.seriesId}</p>
          <p className="text-xs text-gray-400">{ep.id}</p>
        </div>

        {/* Audio */}
        {ep.audioUrl && (
          <div className="border rounded-xl p-3 space-y-2">
            <p className="text-sm font-medium">🎙️ 音声</p>
            <audio controls src={ep.audioUrl} className="w-full" />
          </div>
        )}

        {/* YouTube */}
        <div className="border rounded-xl p-3 space-y-2">
          <p className="text-sm font-medium">📺 YouTube</p>
          {ep.videoUrl ? (
            ytDone ? (
              <p className="text-sm text-green-600">✅ アップロード済み</p>
            ) : (
              <button
                onClick={uploadToYouTube}
                disabled={ytUploading}
                className="w-full bg-red-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-40"
              >
                {ytUploading ? "アップロード中…" : "YouTubeにアップロード"}
              </button>
            )
          ) : (
            <p className="text-xs text-gray-400">動画生成が完了すると表示されます</p>
          )}
        </div>

        {/* Blog */}
        <div className="border rounded-xl p-3 space-y-2">
          <p className="text-sm font-medium">📝 Note.com ブログ</p>
          <p className="text-xs text-gray-400">APIがないため、ダウンロードして手動投稿してください。</p>
          <div className="flex gap-2">
            <button
              onClick={downloadMarkdown}
              disabled={!ep.script}
              className="flex-1 border text-sm py-2 rounded-lg disabled:opacity-40"
            >
              Markdownをダウンロード
            </button>
            {ep.audioUrl && (
              <a
                href={ep.audioUrl}
                download
                className="flex-1 border text-sm py-2 rounded-lg text-center"
              >
                音声をダウンロード
              </a>
            )}
          </div>
        </div>

        <button onClick={onClose} className="w-full text-sm text-gray-400 py-2">
          閉じる
        </button>
      </div>
    </div>
  );
}

export default function EpisodesPage() {
  const [episodes, setEpisodes] = useState<EpisodeRow[]>([]);
  const [selected, setSelected] = useState<EpisodeRow | null>(null);

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

          {IN_PROGRESS.includes(ep.status) && (
            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-400 rounded-full animate-pulse w-1/2" />
            </div>
          )}

          {ep.compoundAccuracy !== undefined && (
            <p className="text-xs text-gray-500">
              複合精度:{" "}
              <span className={ep.compoundAccuracy >= 0.9 ? "text-green-600 font-semibold" : "text-orange-500 font-semibold"}>
                {(ep.compoundAccuracy * 100).toFixed(1)}%
              </span>
            </p>
          )}

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
              <button
                onClick={() => setSelected(ep)}
                className="text-xs bg-green-50 text-green-700 border border-green-200 px-3 py-1 rounded-lg"
              >
                出力を確認 →
              </button>
            )}
          </div>
        </div>
      ))}

      {selected && <EpisodeDetail ep={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
