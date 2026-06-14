import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, MessageSquare, Trash2, Video, Pencil, Check, X } from "lucide-react";
import { useSessions, createSession } from "@/lib/sessions";
import { Button } from "@/components/ui/button";

export function SessionSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { sessions, addSession, deleteSession, updateSession } = useSessions();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { sessionId?: string };
  const active = params.sessionId;
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const handleNew = () => {
    const s = addSession(createSession());
    navigate({ to: "/$sessionId", params: { sessionId: s.id } });
    onNavigate?.();
  };

  const startEditing = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const saveTitle = (id: string) => {
    const trimmed = editTitle.trim();
    if (trimmed) {
      updateSession(id, (s) => ({ ...s, title: trimmed }));
    }
    setEditingId(null);
    setEditTitle("");
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditTitle("");
  };

  return (
    <div className="flex h-full flex-col glass holo-border rounded-2xl m-2 overflow-hidden">
      <div className="p-4 border-b border-[color-mix(in_oklch,var(--color-holo)_30%,transparent)]">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-7 w-7 rounded-md holo-border flex items-center justify-center">
            <Video className="h-4 w-4 text-[var(--color-holo)]" />
          </div>
          <h1 className="holo-text text-sm font-bold tracking-wider uppercase">
            Chat with your video
          </h1>
        </div>
        
        <Button
          onClick={handleNew}
          className="w-full bg-transparent holo-border holo-text text-white hover:bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)]"
        >
          <Plus className="h-4 w-4 mr-2 text-white" />
          New session
        </Button>

      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-8 px-4">
            No sessions yet. Create one to get started.
          </p>
        )}
        {sessions.map((s) => {
          const isActive = s.id === active;
          const isEditing = editingId === s.id;
          return (
            <div
              key={s.id}
              className={`group relative rounded-lg px-3 py-2 cursor-pointer transition-all ${
                isActive
                  ? "holo-border bg-[color-mix(in_oklch,var(--color-holo)_12%,transparent)]"
                  : "hover:bg-[color-mix(in_oklch,var(--color-holo)_6%,transparent)] border border-transparent"
              }`}
            >
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <MessageSquare
                    className={`h-4 w-4 shrink-0 ${
                      isActive ? "text-[var(--color-holo)]" : "text-muted-foreground"
                    }`}
                  />
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveTitle(s.id);
                      if (e.key === "Escape") cancelEditing();
                    }}
                    className="flex-1 bg-transparent border-b border-[var(--color-holo)] outline-none text-sm holo-text py-0.5"
                    autoFocus
                  />
                  <button
                    onClick={() => saveTitle(s.id)}
                    className="p-1 rounded hover:bg-[color-mix(in_oklch,var(--color-holo)_20%,transparent)] text-[var(--color-holo)]"
                    aria-label="Save"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
                    aria-label="Cancel"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <>
                  <Link
                    to="/$sessionId"
                    params={{ sessionId: s.id }}
                    onClick={() => onNavigate?.()}
                    className="flex items-start gap-2 pr-14"
                  >
                    <MessageSquare
                      className={`h-4 w-4 mt-0.5 shrink-0 ${
                        isActive ? "text-[var(--color-holo)]" : "text-muted-foreground"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-sm truncate ${
                          isActive ? "holo-text font-medium" : "text-foreground"
                        }`}
                      >
                        {s.title}
                      </p>
                    </div>
                  </Link>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      startEditing(s.id, s.title);
                    }}
                    className="absolute right-8 top-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-[color-mix(in_oklch,var(--color-holo)_20%,transparent)] text-muted-foreground hover:text-[var(--color-holo)]"
                    aria-label="Edit title"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      const remaining = sessions.filter((x) => x.id !== s.id);
                      deleteSession(s.id);
                      if (isActive) {
                        if (remaining[0]) {
                          navigate({ to: "/$sessionId", params: { sessionId: remaining[0].id } });
                        } else {
                          navigate({ to: "/" });
                        }
                      }
                    }}
                    className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
                    aria-label="Delete session"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-3 border-t border-[color-mix(in_oklch,var(--color-holo)_30%,transparent)] text-[10px] text-muted-foreground text-center">
        By Nguyen Trung, 2026.
      </div>
    </div>
  );
}
