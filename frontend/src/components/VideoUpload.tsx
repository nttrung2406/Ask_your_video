import { useRef, useState } from "react";
import { Upload, Film, AlertCircle, Loader2, CheckCircle2, X, Cloud, Server } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  probeVideo,
  transcodeTo480p,
  isFFmpegSupported,
  MAX_DURATION_SEC,
  TARGET_HEIGHT,
} from "@/lib/videoTranscoder";
import { uploadVideo, waitForPreprocessing, type VideoMeta as ApiVideoMeta, type PreprocessingProgress } from "@/lib/api/video";
import type { Session, VideoMeta } from "@/lib/sessions";

type UploadStatus = "idle" | "probing" | "transcoding" | "uploading" | "preprocessing" | "ready" | "error";

type Props = {
  session: Session;
  onVideo: (meta: VideoMeta, fileUrl: string, backendSessionId?: string) => void;
  onPreprocessingUpdate?: (status: "uploading" | "preprocessing" | "ready" | "error", error?: string) => void;
};

export function VideoUpload({ session, onVideo, onPreprocessingUpdate }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [info, setInfo] = useState<VideoMeta | null>(session.video ?? null);
  const [drag, setDrag] = useState(false);
  const [backendSessionId, setBackendSessionId] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [processingMessage, setProcessingMessage] = useState<string>("Processing video on server...");

  const handleFile = async (file: File) => {
    setError(null);
    setStatus("probing");
    setProgress(0);
    console.log("[VideoUpload] Starting file processing:");
    try {
      console.log("[VideoUpload] Probing video...");
      const probe = await probeVideo(file);
      console.log("[VideoUpload] Probe result:", probe);

      if (probe.durationSec > MAX_DURATION_SEC) {
        throw new Error(
          `Video is ${(probe.durationSec / 60).toFixed(1)} minutes. Maximum is 30 minutes.`,
        );
      }

      let finalFile = file;
      let transcoded = false;

      if (probe.height > TARGET_HEIGHT) {
        if (isFFmpegSupported()) {
          setStatus("transcoding");
          finalFile = await transcodeTo480p(file, (r) => setProgress(r));
          transcoded = true;
        } else {
          // Cannot transcode in this environment — accept original with warning.
          setError(
            `Browser cannot transcode here (SharedArrayBuffer disabled). Using original ${probe.height}p.`,
          );
        }
      }

      const url = URL.createObjectURL(finalFile);
      const meta: VideoMeta = {
        name: finalFile.name,
        size: finalFile.size,
        durationSec: probe.durationSec,
        width: transcoded ? Math.round((probe.width * TARGET_HEIGHT) / probe.height) : probe.width,
        height: transcoded ? TARGET_HEIGHT : probe.height,
        transcoded,
      };
      
      setInfo(meta);
      setPreviewUrl(url);
      setCurrentFile(finalFile);
      
      // Upload to backend
      console.log("[VideoUpload] Starting upload to backend...");
      setStatus("uploading");
      setProgress(0);
      
      const apiMeta: ApiVideoMeta = {
        name: meta.name,
        size: meta.size,
        durationSec: meta.durationSec,
        width: meta.width,
        height: meta.height,
        transcoded: meta.transcoded,
      };
      
      console.log("[VideoUpload] Calling uploadVideo API");
      const uploadResult = await uploadVideo(finalFile, apiMeta, session.id, true);
      console.log("[VideoUpload] Upload done");
      
      if (!uploadResult.session_id) {
        throw new Error("Backend did not return session_id");
      }
      
      setBackendSessionId(uploadResult.session_id);
      console.log("[VideoUpload] Backend session ID:");
      
      // Immediately show video preview and update session with backendSessionId
      onVideo(meta, url, uploadResult.session_id);
      
      // Start preprocessing status tracking
      setStatus("preprocessing");
      setProcessingMessage("Processing video on server...");
      onPreprocessingUpdate?.("preprocessing");
      
      try {
        await waitForPreprocessing(uploadResult.session_id, 600000, 3000, (progress: PreprocessingProgress) => {
          if (progress.status === "waiting_for_model") {
            setProcessingMessage("Model service is starting up, please wait...");
          } else if (progress.status === "retrying") {
            setProcessingMessage(progress.message);
          } else {
            setProcessingMessage("Processing video on server...");
          }
        });
        
        setStatus("ready");
        onPreprocessingUpdate?.("ready");
      } catch (preprocessError: any) {
        setError(preprocessError?.message ?? "Preprocessing failed");
        setStatus("ready"); // Still show video preview even if preprocessing failed
        onPreprocessingUpdate?.("error", preprocessError?.message);
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to process video");
      setStatus("error");
    }
  };

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  const reset = () => {
    setInfo(null);
    setPreviewUrl(null);
    setStatus("idle");
    setError(null);
    setBackendSessionId(null);
    setCurrentFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="glass holo-border rounded-2xl p-4 h-full flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <h2 className="holo-text text-xs font-bold uppercase tracking-widest flex items-center gap-2">
          <Film className="h-4 w-4" />
          Video Source
        </h2>
        {info && (
          <button
            onClick={reset}
            className="text-xs text-muted-foreground hover:text-[var(--color-holo)] flex items-center gap-1"
          >
            <X className="h-3 w-3" /> Replace
          </button>
        )}
      </div>

      {!info && (
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          className={`flex-1 flex flex-col items-center justify-center rounded-xl border-2 border-dashed cursor-pointer transition-all p-6 text-center min-h-[180px] ${
            drag
              ? "border-[var(--color-holo)] bg-[color-mix(in_oklch,var(--color-holo)_10%,transparent)]"
              : "border-[color-mix(in_oklch,var(--color-holo)_40%,transparent)] hover:bg-[color-mix(in_oklch,var(--color-holo)_5%,transparent)]"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={onPick}
            disabled={status !== "idle" && status !== "error"}
          />
          {status === "idle" && (
            <>
              <Upload className="h-10 w-10 text-[var(--color-holo)] mb-3" />
              <p className="text-sm font-medium holo-text">Drop a video or click to upload</p>
              <p className="text-xs text-muted-foreground mt-2 max-w-sm">
                Any format · Max 30 min
              </p>
            </>
          )}
          {(status === "probing" || status === "transcoding") && (
            <>
              <Loader2 className="h-10 w-10 text-[var(--color-holo)] mb-3 animate-spin" />
              <p className="text-sm holo-text">
                {status === "probing" ? "Reading video…" : "Transcoding to 480p…"}
              </p>
              {status === "transcoding" && (
                <div className="w-full max-w-xs mt-3 h-1.5 rounded-full bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)] overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-holo)] transition-all"
                    style={{ width: `${Math.round(progress * 100)}%` }}
                  />
                </div>
              )}
            </>
          )}
          {status === "uploading" && (
            <>
              <Cloud className="h-10 w-10 text-[var(--color-holo)] mb-3 animate-pulse" />
              <p className="text-sm holo-text">Uploading to server…</p>
            </>
          )}
          {status === "preprocessing" && (
            <>
              <Server className="h-10 w-10 text-[var(--color-holo)] mb-3 animate-pulse" />
              <p className="text-sm holo-text">{processingMessage}</p>
              <p className="text-xs text-muted-foreground mt-1">Extracting audio &amp; keyframes</p>
            </>
          )}
          {status === "error" && (
            <>
              <AlertCircle className="h-10 w-10 text-destructive mb-3" />
              <p className="text-sm text-destructive">{error}</p>
              <Button
                onClick={(e) => {
                  e.preventDefault();
                  setStatus("idle");
                }}
                className="mt-3 bg-transparent holo-border holo-text"
              >
                Try again
              </Button>
            </>
          )}
        </label>
      )}

      {info && previewUrl && (
        <div className="flex-1 flex flex-col gap-3 min-h-0">
          <div className="rounded-xl overflow-hidden holo-border bg-black flex-1 min-h-0 relative">
            <video
              src={previewUrl}
              controls
              className="w-full h-full object-contain"
            />
            <div className="absolute inset-0 pointer-events-none scanlines opacity-30" />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <Stat label="Duration" value={`${(info.durationSec / 60).toFixed(1)} min`} />
            <Stat label="Resolution" value={`${info.width}×${info.height}`} />
            <Stat label="Size" value={`${(info.size / 1024 / 1024).toFixed(1)} MB`} />
            <Stat
              label="Status"
              value={info.transcoded ? "480p ✓" : `${info.height}p`}
              icon={info.transcoded ? <CheckCircle2 className="h-3 w-3" /> : null}
            />
          </div>
          {error && (
            <p className="text-xs text-amber-400 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" /> {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg holo-border px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="text-sm holo-text font-medium flex items-center gap-1">
        {value} {icon}
      </p>
    </div>
  );
}
