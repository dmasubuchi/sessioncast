/**
 * Firebase Storage helpers — uploads conference photos to GCS.
 *
 * Firebase Storage paths map directly to GCS:
 *   Storage: episodes/{episodeId}/slides/image.jpg
 *   GCS URI: gs://{storageBucket}/episodes/{episodeId}/slides/image.jpg
 */

import { getStorage, ref, uploadBytesResumable, getDownloadURL } from "firebase/storage";
import app from "./firebase";

const storage = getStorage(app);

const ALLOWED_MIME_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/heic"]);
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export interface UploadResult {
  gcs_uri: string;
  download_url: string;
  filename: string;
}

export interface UploadProgress {
  filename: string;
  percent: number;
  done: boolean;
  error?: string;
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 100);
}

function validateImageFile(file: File): string | null {
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return `${file.name}: サポートされていないファイル形式 (${file.type})`;
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `${file.name}: ファイルサイズが上限 (20MB) を超えています`;
  }
  return null;
}

export async function uploadImage(
  file: File,
  episodeId: string,
  folder: "slides" | "atmosphere" | "general",
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadResult> {
  const validationError = validateImageFile(file);
  if (validationError) throw new Error(validationError);

  const safeName = sanitizeFilename(file.name);
  const timestamp = Date.now();
  const storagePath = `episodes/${episodeId}/${folder}/${timestamp}_${safeName}`;
  const storageRef = ref(storage, storagePath);

  return new Promise((resolve, reject) => {
    const task = uploadBytesResumable(storageRef, file, { contentType: file.type });

    task.on(
      "state_changed",
      (snapshot) => {
        const percent = Math.round((snapshot.bytesTransferred / snapshot.totalBytes) * 100);
        onProgress?.({ filename: file.name, percent, done: false });
      },
      (error) => {
        onProgress?.({ filename: file.name, percent: 0, done: true, error: error.message });
        reject(error);
      },
      async () => {
        const download_url = await getDownloadURL(task.snapshot.ref);
        const storageBucket = process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET ?? "";
        const gcs_uri = `gs://${storageBucket}/${storagePath}`;
        onProgress?.({ filename: file.name, percent: 100, done: true });
        resolve({ gcs_uri, download_url, filename: safeName });
      }
    );
  });
}

export async function uploadImages(
  files: File[],
  episodeId: string,
  folder: "slides" | "atmosphere" | "general",
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadResult[]> {
  const results = await Promise.allSettled(
    files.map((file) => uploadImage(file, episodeId, folder, onProgress))
  );

  const succeeded: UploadResult[] = [];
  for (const result of results) {
    if (result.status === "fulfilled") {
      succeeded.push(result.value);
    } else {
      console.error("Upload failed:", result.reason?.message);
    }
  }
  return succeeded;
}
