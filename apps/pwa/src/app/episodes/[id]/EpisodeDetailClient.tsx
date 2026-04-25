"use client";

import { useEffect, useState } from "react";
import { subscribeToEpisode, type Episode } from "@/lib/firestore";

export default function EpisodeDetailClient({ id }: { id: string }) {
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [ytUploading, setYtUploading] = useState(false);
  const [ytDone, setYtDone] = useState(false);

  useEffect(() => {
    if (!id) return;
    return subscribeToEpisode(id, setEpisode);
  }, [id]);

  const downloadMarkdown = () => {
    if (!episode?.script) return;
    const blob = new Blob([episode.script], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const uploadToYouTube = async () => {
    setYtUploading(true);
    await new Promise((r) => setTimeout(r, 1500));
    setYtDone(true);
    setYtUploading(false);
  };

  if (!episode) {
    return <div className="max-w-lg mx-auto px-4 py-8 text-sm text-gray-400">読み込み中…</div>;
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-lg font-bold">{episode.seriesId}</h1>
        <p className="text-xs text-gray-400">{id}</p>
      </div>

      {/* Audio */}
      {episode.audioUrl && (
        <div className="border rounded-xl p-4 space-y-2">
          <p className="text-sm font-medium">🎙️ 音声</p>
          <audio controls src={episode.audioUrl} className="w-full" />
        </div>
      )}

      {/* YouTube */}
      <div className="border rounded-xl p-4 space-y-3">
        <p className="text-sm font-medium">📺 YouTube</p>
        {episode.videoUrl ? (
          <div className="space-y-2">
            <p className="text-xs text-gray-500">動画ファイル準備完了</p>
            {ytDone ? (
              <p className="text-sm text-green-600">✅ アップロード済み</p>
            ) : (
              <button
                onClick={uploadToYouTube}
                disabled={ytUploading}
                className="w-full bg-red-600 text-white py-2.5 rounded-lg text-sm font-medium disabled:opacity-40"
              >
                {ytUploading ? "アップロード中…" : "YouTubeにアップロード"}
              </button>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-400">動画生成が完了すると表示されます</p>
        )}
      </div>

      {/* Blog */}
      <div className="border rounded-xl p-4 space-y-3">
        <p className="text-sm font-medium">📝 ブログ記事 (Note.com)</p>
        <p className="text-xs text-gray-500">
          Note.com にはAPIがないため、Markdownと音声をダウンロードして手動で投稿してください。
        </p>
        <div className="flex gap-2">
          <button
            onClick={downloadMarkdown}
            disabled={!episode.script}
            className="flex-1 border text-sm py-2 rounded-lg disabled:opacity-40"
          >
            Markdownをダウンロード
          </button>
          <a
            href={episode.audioUrl ?? "#"}
            download
            className={`flex-1 border text-sm py-2 rounded-lg text-center ${!episode.audioUrl ? "opacity-40 pointer-events-none" : ""}`}
          >
            音声をダウンロード
          </a>
        </div>
      </div>
    </div>
  );
}
