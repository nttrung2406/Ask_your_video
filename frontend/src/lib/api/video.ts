/**
 * Video API functions for communicating with the backend
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8082";

export type VideoMeta = {
  name: string;
  size: number;
  durationSec: number;
  width: number;
  height: number;
  transcoded: boolean;
};

export type UploadResponse = {
  session_id: string;
  status: string;
  message: string;
};

export type SessionResponse = {
  session_id: string;
  status: string;
  video_name: string | null;
  video_size: number | null;
  is_preprocessed: boolean;
  error_message: string | null;
};

export type AskQuestionResponse = {
  session_id: string;
  question: string;
  answer: string;
  thinking_process: string | null;
};

/**
 * Upload a video file to the backend
 * @param file The video file to upload
 * @param meta Video metadata from frontend processing
 * @param sessionId Optional session ID (will be generated if not provided)
 * @param autoPreprocess Whether to start preprocessing immediately (default: true)
 */
export async function uploadVideo(
  file: File,
  meta: VideoMeta,
  sessionId?: string,
  autoPreprocess: boolean = true,
): Promise<UploadResponse> {
  console.log("[API] uploadVideo called");
  console.log("[API] Backend URL:");
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", meta.name);
  formData.append("size", meta.size.toString());
  formData.append("durationSec", meta.durationSec.toString());
  formData.append("width", meta.width.toString());
  formData.append("height", meta.height.toString());
  formData.append("transcoded", meta.transcoded.toString());
  formData.append("auto_preprocess", autoPreprocess.toString());
  
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  console.log("[API] Sending fetch to backend");
  const response = await fetch(`${BACKEND_URL}/api/video/upload`, {
    method: "POST",
    body: formData,
  });
  console.log("[API] Response status:", response.status);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

/**
 * Manually trigger preprocessing for an uploaded video
 */
export async function preprocessVideo(sessionId: string): Promise<{
  session_id: string;
  status: string;
  frame_count: number | null;
  audio_path: string | null;
  message: string;
}> {
  const response = await fetch(`${BACKEND_URL}/api/video/preprocess/${sessionId}`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Preprocessing failed" }));
    throw new Error(error.detail || "Preprocessing failed");
  }

  return response.json();
}

/**
 * Get session information
 */
export async function getSession(sessionId: string): Promise<SessionResponse> {
  const response = await fetch(`${BACKEND_URL}/api/video/session/${sessionId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Session not found" }));
    throw new Error(error.detail || "Session not found");
  }

  return response.json();
}

export type PreprocessingProgress = {
  status: "polling" | "retrying" | "waiting_for_model";
  message: string;
  attempt?: number;
};

/**
 * Poll for session status until preprocessing is complete
 * Handles model service unavailability gracefully with retries
 */
export async function waitForPreprocessing(
  sessionId: string,
  maxWaitMs: number = 600000, // 10 minutes (model service may be slow to start)
  pollIntervalMs: number = 3000,
  onProgress?: (progress: PreprocessingProgress) => void,
): Promise<SessionResponse> {
  const startTime = Date.now();
  let consecutiveErrors = 0;
  const maxConsecutiveErrors = 10;

  while (Date.now() - startTime < maxWaitMs) {
    try {
      const session = await getSession(sessionId);
      consecutiveErrors = 0; // Reset on success

      if (session.status === "preprocessed" || session.status === "ready") {
        return session;
      }

      if (session.status === "error") {
        // Check if it's a model service connection error
        if (session.error_message?.includes("name resolution") ||
            session.error_message?.includes("Connection refused") ||
            session.error_message?.includes("ConnectError")) {
          onProgress?.({
            status: "waiting_for_model",
            message: "Model service is starting up, please wait...",
          });
          await new Promise((resolve) => setTimeout(resolve, pollIntervalMs * 2));
          continue;
        }
        throw new Error(session.error_message || "Preprocessing failed");
      }

      onProgress?.({
        status: "polling",
        message: "Processing video on server...",
      });

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    } catch (err: any) {
      consecutiveErrors++;
      
      // Network or fetch errors - retry with backoff
      if (consecutiveErrors < maxConsecutiveErrors) {
        onProgress?.({
          status: "retrying",
          message: `Connection issue, retrying... (${consecutiveErrors}/${maxConsecutiveErrors})`,
          attempt: consecutiveErrors,
        });
        await new Promise((resolve) => setTimeout(resolve, pollIntervalMs * Math.min(consecutiveErrors, 3)));
        continue;
      }
      
      throw new Error("Unable to connect to server. Please check if services are running.");
    }
  }

  throw new Error("Preprocessing is taking longer than expected. The video may still be processing.");
}

/**
 * Ask a question about a preprocessed video
 * Uses the reasoning module endpoint with KV cache optimization
 */
export async function askQuestion(
  sessionId: string,
  question: string,
  vlmPrompt?: string,
): Promise<AskQuestionResponse> {
  const response = await fetch(`${BACKEND_URL}/api/reasoning/ask/${sessionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      vlm_prompt: vlmPrompt,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Question failed" }));
    throw new Error(error.detail || "Question failed");
  }

  return response.json();
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/video/session/${sessionId}`, {
    method: "DELETE",
  });

  if (!response.ok && response.status !== 404) {
    const error = await response.json().catch(() => ({ detail: "Delete failed" }));
    throw new Error(error.detail || "Delete failed");
  }
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  model_service: string;
  cache: string;
}> {
  const response = await fetch(`${BACKEND_URL}/api/video/health`);
  return response.json();
}
