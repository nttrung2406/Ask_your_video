import { useEffect, useState, useCallback } from "react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
};

export type VideoMeta = {
  name: string;
  size: number;
  durationSec: number;
  width: number;
  height: number;
  transcoded: boolean;
  dataUrl?: string; // small previews only; large videos stored as object URL ephemeral
};

export type Session = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  video?: VideoMeta;
  backendSessionId?: string; // Backend session ID for API calls
  preprocessingStatus?: "uploading" | "preprocessing" | "ready" | "error"; // Video processing status
  preprocessingError?: string; // Error message if preprocessing failed
  messages: ChatMessage[];
};

const KEY = "holo.sessions.v1";

function read(): Session[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Session[];
  } catch {
    return [];
  }
}

function write(sessions: Session[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(KEY, JSON.stringify(sessions));
  } catch (e) {
    console.warn("Failed to save sessions", e);
  }
}

export function createSession(title?: string): Session {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: title ?? `Session ${new Date(now).toLocaleString()}`,
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

let listeners = new Set<() => void>();
function emit() {
  listeners.forEach((l) => l());
}

export function useSessions() {
  // Initialize with empty array to avoid hydration mismatch
  // localStorage is only available on client after hydration
  const [sessions, setSessions] = useState<Session[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Load from localStorage after hydration
  useEffect(() => {
    setSessions(read());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const l = () => setSessions(read());
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  }, [hydrated]);

  const persist = useCallback((next: Session[]) => {
    write(next);
    setSessions(next);
    emit();
  }, []);

  const addSession = useCallback(
    (s?: Session) => {
      const created = s ?? createSession();
      const next = [created, ...read()];
      persist(next);
      return created;
    },
    [persist],
  );

  const updateSession = useCallback(
    (id: string, patch: Partial<Session> | ((s: Session) => Session)) => {
      const current = read();
      const next = current.map((s) => {
        if (s.id !== id) return s;
        const updated = typeof patch === "function" ? patch(s) : { ...s, ...patch };
        return { ...updated, updatedAt: Date.now() };
      });
      persist(next);
    },
    [persist],
  );

  const deleteSession = useCallback(
    (id: string) => {
      persist(read().filter((s) => s.id !== id));
    },
    [persist],
  );

  return { sessions, addSession, updateSession, deleteSession };
}

export function getSession(id: string): Session | undefined {
  return read().find((s) => s.id === id);
}
