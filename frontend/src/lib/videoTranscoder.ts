// Client-side video probing + optional ffmpeg.wasm transcoding to 480p.
// ffmpeg.wasm requires cross-origin isolation (SharedArrayBuffer). If the
// environment doesn't allow it, we fall back to validation-only.

export type ProbeResult = {
  durationSec: number;
  width: number;
  height: number;
};

export const MAX_DURATION_SEC = 30 * 60; // 30 minutes
export const TARGET_HEIGHT = 480;

export function probeVideo(file: File): Promise<ProbeResult> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    v.preload = "metadata";
    v.muted = true;
    v.src = url;
    v.onloadedmetadata = () => {
      const out = {
        durationSec: v.duration || 0,
        width: v.videoWidth || 0,
        height: v.videoHeight || 0,
      };
      URL.revokeObjectURL(url);
      resolve(out);
    };
    v.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read video metadata. Unsupported format?"));
    };
  });
}

export function isFFmpegSupported(): boolean {
  // crossOriginIsolated is the definitive check for SharedArrayBuffer availability
  // It's true when COOP: same-origin and COEP: require-corp headers are set
  if (typeof window === "undefined") return false;
  if (typeof crossOriginIsolated !== "undefined" && crossOriginIsolated) {
    return true;
  }
  // Fallback check for environments where crossOriginIsolated may not be defined
  return typeof SharedArrayBuffer !== "undefined";
}

let ffmpegSingleton: any | null = null;
async function getFFmpeg(onLog?: (m: string) => void) {
  if (ffmpegSingleton) return ffmpegSingleton;
  const { FFmpeg } = await import("@ffmpeg/ffmpeg");
  const ff = new FFmpeg();
  if (onLog) ff.on("log", ({ message }: { message: string }) => onLog(message));
  const base = "https://unpkg.com/@ffmpeg/core@0.12.10/dist/esm";
  await ff.load({
    coreURL: `${base}/ffmpeg-core.js`,
    wasmURL: `${base}/ffmpeg-core.wasm`,
  });
  ffmpegSingleton = ff;
  return ff;
}

export async function transcodeTo480p(
  file: File,
  onProgress?: (ratio: number) => void,
): Promise<File> {
  if (!isFFmpegSupported()) {
    throw new Error("FFmpeg unavailable: cross-origin isolation (SharedArrayBuffer) not enabled.");
  }
  const { fetchFile } = await import("@ffmpeg/util");
  const ff = await getFFmpeg();
  if (onProgress) ff.on("progress", ({ progress }: { progress: number }) => onProgress(progress));

  const inName = "input" + (file.name.match(/\.[a-zA-Z0-9]+$/)?.[0] ?? ".mp4");
  const outName = "output.mp4";
  await ff.writeFile(inName, await fetchFile(file));

  // Scale: keep aspect, height=480, width auto, even
  await ff.exec([
    "-i", inName,
    "-vf", `scale=-2:${TARGET_HEIGHT}`,
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "28",
    "-c:a", "aac",
    "-b:a", "96k",
    "-movflags", "+faststart",
    outName,
  ]);

  const data = (await ff.readFile(outName)) as Uint8Array;
  const buf = new Uint8Array(data.byteLength);
  buf.set(data);
  const blob = new Blob([buf.buffer], { type: "video/mp4" });
  return new File([blob], file.name.replace(/\.[^.]+$/, "") + "-480p.mp4", { type: "video/mp4" });
}
