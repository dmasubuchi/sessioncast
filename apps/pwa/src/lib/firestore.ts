/**
 * Firestore schema helpers for SessionCast
 *
 * Collections:
 *   sessions/{sessionId}          — conference session notes + metadata
 *   episodes/{episodeId}          — generated episode content + pipeline state
 *   series/{seriesId}             — radio series config + persona
 *   pipeline_runs/{runId}         — pipeline execution log (accuracy, latency)
 */

import {
  collection,
  doc,
  addDoc,
  updateDoc,
  onSnapshot,
  serverTimestamp,
  type DocumentData,
  type Unsubscribe,
} from "firebase/firestore";
import { db } from "./firebase";

// --- Types ---

export type PipelineStatus =
  | "pending"
  | "researching"
  | "writing"
  | "tts"
  | "rendering"
  | "publishing"
  | "done"
  | "error";

export interface SessionNote {
  title: string;
  notes: string;
  eventId: string;
  speakerName?: string;
  tags: string[];
  createdAt?: DocumentData;
}

export interface Episode {
  sessionId: string;
  seriesId: string;
  status: PipelineStatus;
  script?: string;
  audioUrl?: string;
  videoUrl?: string;
  compoundAccuracy?: number;
  contextTokensMax?: number;
  createdAt?: DocumentData;
  updatedAt?: DocumentData;
}

// --- Session notes ---

export async function createSession(data: SessionNote): Promise<string> {
  const ref = await addDoc(collection(db, "sessions"), {
    ...data,
    createdAt: serverTimestamp(),
  });
  return ref.id;
}

// --- Episode pipeline state ---

export async function createEpisode(data: Omit<Episode, "createdAt" | "updatedAt">): Promise<string> {
  const ref = await addDoc(collection(db, "episodes"), {
    ...data,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  });
  return ref.id;
}

export async function updateEpisodeStatus(
  episodeId: string,
  status: PipelineStatus,
  extra?: Partial<Episode>
): Promise<void> {
  await updateDoc(doc(db, "episodes", episodeId), {
    status,
    ...extra,
    updatedAt: serverTimestamp(),
  });
}

export function subscribeToEpisode(
  episodeId: string,
  callback: (episode: Episode) => void
): Unsubscribe {
  return onSnapshot(doc(db, "episodes", episodeId), (snap) => {
    if (snap.exists()) callback(snap.data() as Episode);
  });
}
