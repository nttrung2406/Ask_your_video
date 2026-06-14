import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { useSessions, createSession } from "@/lib/sessions";
import { SessionSidebar } from "@/components/SessionSidebar";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Chat with your video" },
      { name: "description", content: "Upload a video and ask AI anything about it." },
    ],
  }),
  component: Index,
});

function Index() {
  const navigate = useNavigate();
  const { sessions, addSession } = useSessions();
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState<boolean | null>(null);

  // Initialize on client only to avoid hydration mismatch
  useEffect(() => {
    if (desktopSidebarOpen === null) {
      setDesktopSidebarOpen(true);
    }
  }, [desktopSidebarOpen]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (sessions.length > 0) {
      navigate({ to: "/$sessionId", params: { sessionId: sessions[0].id }, replace: true });
    }
  }, [sessions, navigate]);

  const handleStart = () => {
    const s = addSession(createSession());
    navigate({ to: "/$sessionId", params: { sessionId: s.id } });
  };

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Desktop collapsed toggle button */}
      {desktopSidebarOpen === false && (
        <button
          onClick={() => setDesktopSidebarOpen(true)}
          className="hidden md:flex fixed left-2 top-2 z-50 h-10 w-10 rounded-lg holo-border holo-text items-center justify-center hover:bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)] transition-colors"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
      )}
      
      <aside className={`hidden md:flex shrink-0 transition-all duration-300 ease-in-out ${
        desktopSidebarOpen ? "w-72" : "w-0 -translate-x-full"
      }`}>
        {/* Desktop close button inside sidebar */}
        <button
          onClick={() => setDesktopSidebarOpen(false)}
          className="hidden md:flex absolute right-2 top-4 z-10 h-8 w-8 rounded-lg holo-border holo-text items-center justify-center hover:bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)] transition-colors"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4" />
        </button>
        <SessionSidebar />
      </aside>
      <main className={`flex-1 flex items-center justify-center p-6 transition-all duration-300 ${
        desktopSidebarOpen === false ? "md:pl-14" : ""
      }`}>
        <div className="text-center max-w-md glass holo-border rounded-2xl p-8">
          <h1 className="holo-text text-2xl font-bold tracking-wide mb-2">
            Video Q&A
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            Upload a video (up to 30 min, auto-downscaled to 480p) and chat with an AI about it.
          </p>
          <button
            onClick={handleStart}
            className="px-5 py-2.5 rounded-lg holo-border holo-text hover:bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)] transition"
          >
            Start a new session
          </button>
        </div>
      </main>
    </div>
  );
}
