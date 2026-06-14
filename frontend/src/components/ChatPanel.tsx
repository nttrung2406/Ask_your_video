import { useEffect, useRef, useState } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { askQuestion } from "@/lib/api/video";
import type { ChatMessage, Session } from "@/lib/sessions";

type Props = {
  session: Session;
  onSend: (userMsg: ChatMessage, assistantMsg: ChatMessage) => void;
};

export function ChatPanel({ session, onSend }: Props) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [session.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [session.messages.length, sending]);

  const submit = async () => {
    const text = input.trim();
    if (!text || sending) return;
    
    // Check if video is uploaded and backend session exists
    if (!session.video || !session.backendSessionId) {
      setError("Please upload a video first before asking questions.");
      return;
    }
    
    // Check if preprocessing is complete
    if (session.preprocessingStatus === "preprocessing") {
      setError("Please wait for video processing to complete.");
      return;
    }
    
    if (session.preprocessingStatus === "error") {
      setError("Video processing failed. Please try uploading again.");
      return;
    }
    
    setSending(true);
    setInput("");
    setError(null);
    
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };
    
    try {
      // Call the real backend API
      const response = await askQuestion(session.backendSessionId, text);
      
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        createdAt: Date.now(),
      };
      
      onSend(userMsg, assistantMsg);
    } catch (err: any) {
      // Show error but still save user message
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Sorry, I couldn't process your question. ${err?.message || "Please try again."}`,
        createdAt: Date.now(),
      };
      onSend(userMsg, errorMsg);
      setError(err?.message || "Failed to get response");
    } finally {
      setSending(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="glass holo-border rounded-2xl h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-[color-mix(in_oklch,var(--color-holo)_30%,transparent)] flex items-center gap-2">
        <Bot className="h-4 w-4 text-[var(--color-holo)]" />
        <h2 className="holo-text text-xs font-bold uppercase tracking-widest">
          Q&A Interpreter
        </h2>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {session.messages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-sm">
              {session.preprocessingStatus === "preprocessing" ? (
                <>
                  <Loader2 className="h-8 w-8 text-[var(--color-holo)] mx-auto mb-3 animate-spin" />
                  <p className="text-sm text-muted-foreground">
                    Processing your video...
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    You can ask questions once processing is complete.
                  </p>
                </>
              ) : session.preprocessingStatus === "ready" ? (
                <p className="text-sm text-muted-foreground">
                  Video ready! Ask anything about it.
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Ask anything.
                </p>
              )}
            </div>
          </div>
        )}
        {session.messages.map((m) => (
          <Bubble key={m.id} msg={m} />
        ))}
        {sending && (
          <div className="flex items-start gap-2">
            <Avatar role="assistant" />
            <div className="bubble-assistant">
              <span className="inline-flex gap-1">
                <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-[color-mix(in_oklch,var(--color-holo)_30%,transparent)]">
        {error && (
          <div className="mb-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-xs">
            {error}
          </div>
        )}
        {!session.video && (
          <div className="mb-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs">
            Upload a video first to start asking questions.
          </div>
        )}
        {session.video && session.preprocessingStatus === "preprocessing" && (
          <div className="mb-2 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs flex items-center gap-2">
            <Loader2 className="h-3 w-3 animate-spin" />
            Processing video... Please wait before asking questions.
          </div>
        )}
        {session.video && session.preprocessingStatus === "error" && (
          <div className="mb-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-xs">
            Video processing failed: {session.preprocessingError || "Unknown error"}. Please try uploading again.
          </div>
        )}
        {session.video && !session.backendSessionId && session.preprocessingStatus !== "preprocessing" && (
          <div className="mb-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs">
            Session data outdated. Please click "Replace" above and re-upload the video.
          </div>
        )}
        <div className="flex items-end gap-2 holo-border rounded-xl p-2 bg-[color-mix(in_oklch,var(--background)_60%,transparent)]">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setError(null);
            }}
            onKeyDown={onKey}
            placeholder="Ask about the video…"
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-foreground placeholder:text-muted-foreground py-1.5 px-2 max-h-32"
          />
          <button
            onClick={submit}
            disabled={!input.trim() || sending || session.preprocessingStatus === "preprocessing" || !session.backendSessionId}
            className="shrink-0 h-9 w-9 rounded-lg holo-border holo-text flex items-center justify-center hover:bg-[color-mix(in_oklch,var(--color-holo)_18%,transparent)] disabled:opacity-40 disabled:cursor-not-allowed transition"
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>

      <style>{`
        .bubble-user {
          max-width: 80%;
          padding: 0.6rem 0.9rem;
          border-radius: 1rem 1rem 0.25rem 1rem;
          border: 1px solid color-mix(in oklch, var(--color-holo) 70%, transparent);
          background: color-mix(in oklch, var(--color-holo) 10%, transparent);
          color: #fff;
          box-shadow: 0 0 18px color-mix(in oklch, var(--color-holo) 25%, transparent),
                      inset 0 0 12px color-mix(in oklch, var(--color-holo) 8%, transparent);
          backdrop-filter: blur(6px);
          font-size: 0.875rem;
          line-height: 1.4;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
        .bubble-assistant {
          max-width: 80%;
          padding: 0.6rem 0.9rem;
          border-radius: 1rem 1rem 1rem 0.25rem;
          border: 1px solid color-mix(in oklch, var(--color-holo) 55%, transparent);
          background: color-mix(in oklch, var(--color-holo) 6%, transparent);
          color: #fff;
          box-shadow: 0 0 14px color-mix(in oklch, var(--color-holo) 18%, transparent);
          backdrop-filter: blur(6px);
          font-size: 0.875rem;
          line-height: 1.4;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
      `}</style>
    </div>
  );
}

function Bubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div className="flex items-start gap-2 justify-end">
        <div className="bubble-user">{msg.content}</div>
        <Avatar role="user" />
      </div>
    );
  }
  return (
    <div className="flex items-start gap-2">
      <Avatar role="assistant" />
      <div className="bubble-assistant">{msg.content}</div>
    </div>
  );
}

function Avatar({ role }: { role: "user" | "assistant" }) {
  return (
    <div className="h-7 w-7 rounded-full holo-border flex items-center justify-center shrink-0 mt-0.5 bg-[color-mix(in_oklch,var(--background)_60%,transparent)]">
      {role === "user" ? (
        <User className="h-3.5 w-3.5 text-[var(--color-holo)]" />
      ) : (
        <Bot className="h-3.5 w-3.5 text-[var(--color-holo)]" />
      )}
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-holo)] animate-pulse"
      style={{ animationDelay: delay }}
    />
  );
}
