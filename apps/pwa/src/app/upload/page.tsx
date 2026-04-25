"use client";

import { useState, useCallback, useRef } from "react";
import { createEpisode, addImagesToEpisode, type ImageCategory } from "@/lib/firestore";
import { uploadImages, type UploadProgress } from "@/lib/storage";

type CategoryOption = {
  value: ImageCategory;
  label: string;
  emoji: string;
  description: string;
};

const CATEGORIES: CategoryOption[] = [
  {
    value: "slide",
    label: "スライド",
    emoji: "📊",
    description: "セッションのプレゼンスライド",
  },
  {
    value: "atmosphere",
    label: "雰囲気・会場",
    emoji: "🏛️",
    description: "会場・受付・ランチ・レセプション",
  },
  {
    value: "general",
    label: "その他",
    emoji: "📸",
    description: "その他の写真",
  },
];

type UploadState = "idle" | "uploading" | "done" | "error";

interface PreviewFile {
  file: File;
  objectUrl: string;
  progress?: UploadProgress;
}

export default function UploadPage() {
  const [episodeId, setEpisodeId] = useState<string>("");
  const [seriesId, setSeriesId] = useState<string>("google-radio");
  const [selectedCategory, setSelectedCategory] = useState<ImageCategory>("slide");
  const [previews, setPreviews] = useState<PreviewFile[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errors, setErrors] = useState<string[]>([]);
  const [uploadedCount, setUploadedCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const addFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    const imageFiles = Array.from(files).filter((f) => f.type.startsWith("image/"));
    const newPreviews = imageFiles.map((file) => ({
      file,
      objectUrl: URL.createObjectURL(file),
    }));
    setPreviews((prev) => [...prev, ...newPreviews]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const removePreview = (index: number) => {
    setPreviews((prev) => {
      URL.revokeObjectURL(prev[index].objectUrl);
      return prev.filter((_, i) => i !== index);
    });
  };

  const handleUpload = async () => {
    if (previews.length === 0) return;

    setUploadState("uploading");
    setErrors([]);
    setUploadedCount(0);

    // Create episode in Firestore if not yet done
    let targetEpisodeId = episodeId;
    if (!targetEpisodeId) {
      targetEpisodeId = await createEpisode({
        sessionId: "",
        seriesId,
        status: "pending",
        images: [],
      });
      setEpisodeId(targetEpisodeId);
    }

    const onProgress = (progress: UploadProgress) => {
      setPreviews((prev) =>
        prev.map((p) =>
          p.file.name === progress.filename ? { ...p, progress } : p
        )
      );
      if (progress.done && !progress.error) {
        setUploadedCount((n) => n + 1);
      }
    };

    const folder = selectedCategory === "slide" ? "slides" : selectedCategory === "atmosphere" ? "atmosphere" : "general";

    try {
      const uploaded = await uploadImages(
        previews.map((p) => p.file),
        targetEpisodeId,
        folder,
        onProgress
      );

      if (uploaded.length > 0) {
        await addImagesToEpisode(
          targetEpisodeId,
          uploaded.map((u) => ({
            gcs_uri: u.gcs_uri,
            type: selectedCategory,
            filename: u.filename,
          }))
        );
        setUploadState("done");
      } else {
        setUploadState("error");
        setErrors(["アップロードに失敗しました。"]);
      }
    } catch (err: unknown) {
      setUploadState("error");
      setErrors([err instanceof Error ? err.message : String(err)]);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">📷 写真をアップロード</h1>
      <p className="text-gray-500 text-sm mb-6">
        カンファレンスの写真を保存して、ラジオエピソードの素材に使います
      </p>

      {/* Series / Episode ID */}
      <div className="bg-white rounded-xl p-4 mb-4 shadow-sm">
        <label className="block text-sm font-medium text-gray-700 mb-1">シリーズID</label>
        <input
          type="text"
          value={seriesId}
          onChange={(e) => setSeriesId(e.target.value.replace(/[^a-z0-9-]/g, ""))}
          placeholder="google-radio"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {episodeId && (
          <p className="mt-2 text-xs text-gray-400">エピソードID: {episodeId}</p>
        )}
      </div>

      {/* Category Selection */}
      <div className="bg-white rounded-xl p-4 mb-4 shadow-sm">
        <p className="text-sm font-medium text-gray-700 mb-3">写真のカテゴリ</p>
        <div className="grid grid-cols-3 gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value as ImageCategory)}
              className={`flex flex-col items-center p-3 rounded-xl border-2 transition-all text-center ${
                selectedCategory === cat.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <span className="text-2xl mb-1">{cat.emoji}</span>
              <span className="text-xs font-medium text-gray-800">{cat.label}</span>
              <span className="text-xs text-gray-400 mt-0.5 leading-tight">{cat.description}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Drop Zone */}
      <div
        ref={dropZoneRef}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
        className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 mb-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-all shadow-sm"
      >
        <div className="text-4xl mb-2">📤</div>
        <p className="text-gray-600 font-medium">タップまたはドロップで追加</p>
        <p className="text-gray-400 text-sm mt-1">JPEG / PNG / WebP · 最大20MB/枚</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {/* Preview Grid */}
      {previews.length > 0 && (
        <div className="bg-white rounded-xl p-4 mb-4 shadow-sm">
          <p className="text-sm font-medium text-gray-700 mb-3">
            選択中の写真 ({previews.length}枚)
          </p>
          <div className="grid grid-cols-3 gap-2">
            {previews.map((preview, idx) => (
              <div key={idx} className="relative group aspect-square">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview.objectUrl}
                  alt={preview.file.name}
                  className="w-full h-full object-cover rounded-lg"
                />
                {/* Progress overlay */}
                {preview.progress && !preview.progress.done && (
                  <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">{preview.progress.percent}%</span>
                  </div>
                )}
                {preview.progress?.done && !preview.progress.error && (
                  <div className="absolute inset-0 bg-green-500/40 rounded-lg flex items-center justify-center">
                    <span className="text-white text-2xl">✓</span>
                  </div>
                )}
                {/* Remove button */}
                {uploadState === "idle" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); removePreview(idx); }}
                    className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error messages */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-4">
          {errors.map((e, i) => (
            <p key={i} className="text-red-600 text-sm">{e}</p>
          ))}
        </div>
      )}

      {/* Upload button / Status */}
      {uploadState === "done" ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
          <p className="text-green-700 font-medium text-lg">✅ {uploadedCount}枚の写真を保存しました</p>
          <p className="text-green-600 text-sm mt-1">
            エピソード生成時に自動的に解析されます
          </p>
          <p className="text-gray-400 text-xs mt-2">Episode ID: {episodeId}</p>
          <button
            onClick={() => {
              setPreviews([]);
              setUploadState("idle");
              setUploadedCount(0);
            }}
            className="mt-3 text-sm text-blue-600 underline"
          >
            さらに追加する
          </button>
        </div>
      ) : (
        <button
          onClick={handleUpload}
          disabled={previews.length === 0 || uploadState === "uploading"}
          className="w-full py-4 rounded-xl font-bold text-white text-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-700 active:scale-95"
        >
          {uploadState === "uploading"
            ? `アップロード中... (${uploadedCount}/${previews.length})`
            : `${previews.length > 0 ? previews.length + "枚を" : ""}保存する`}
        </button>
      )}
    </main>
  );
}
