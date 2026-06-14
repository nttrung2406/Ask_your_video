import { createFileRoute, useNavigate, useParams } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Menu, X } from "lucide-react";
import { SessionSidebar } from "@/components/SessionSidebar";
import { VideoUpload } from "@/components/VideoUpload";
import { ChatPanel } from "@/components/ChatPanel";
import { useSessions } from "@/lib/sessions";

export const Route = createFileRoute("/$sessionId")({
  head: () => ({
    meta: [
      { title: "Chat with your video" },
      { name: "description", content: "AI Q&A with your video." },
    ],
  }),
  component: SessionPage,
});

function SessionPage() {
  const { sessionId } = useParams({ from: "/$sessionId" });
  const { sessions, updateSession } = useSessions();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopSidebarOpen, setDesktopSidebarOpen] = useState<boolean | null>(null);

  // Initialize on client only to avoid hydration mismatch
  useEffect(() => {
    if (desktopSidebarOpen === null) {
      setDesktopSidebarOpen(true);
    }
  }, [desktopSidebarOpen]);

  const session = useMemo(() => sessions.find((s) => s.id === sessionId), [sessions, sessionId]);

  useEffect(() => {
    if (sessions.length > 0 && !session) {
      navigate({ to: "/", replace: true });
    }
  }, [session, sessions.length, navigate]);

  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Loading session…
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Mobile overlay sidebar */}
      <div
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden transition-opacity ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSidebarOpen(false)}
      />
      
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
      
      {/* Sidebar */}
      <aside
        className={`fixed md:relative z-50 h-full w-72 shrink-0 transition-all duration-300 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } ${
          desktopSidebarOpen ? "md:translate-x-0 md:w-72" : "md:-translate-x-full md:w-0"
        }`}
      >
        {/* Desktop close button inside sidebar */}
        <button
          onClick={() => setDesktopSidebarOpen(false)}
          className="hidden md:flex absolute right-2 top-4 z-10 h-8 w-8 rounded-lg holo-border holo-text items-center justify-center hover:bg-[color-mix(in_oklch,var(--color-holo)_15%,transparent)] transition-colors"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4" />
        </button>
        <SessionSidebar onNavigate={() => setSidebarOpen(false)} />
      </aside>

      <main className={`flex-1 flex flex-col min-w-0 p-2 gap-2 transition-all duration-300 ${
        desktopSidebarOpen === false ? "md:pl-14" : ""
      }`}>
        {/* Mobile header */}
        <div className="md:hidden flex items-center gap-2 px-2 py-1">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="h-9 w-9 rounded-lg holo-border holo-text flex items-center justify-center"
            aria-label="Toggle sessions"
          >
            {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
          <h1 className="holo-text text-sm font-bold truncate">{session.title}</h1>
        </div>

        {/* Stacked content: top = video, bottom = chat. Resizable via CSS grid. */}
        <div className="flex-1 grid grid-rows-[minmax(0,5fr)_minmax(0,7fr)] md:grid-rows-[minmax(0,1fr)_minmax(0,1fr)] gap-2 min-h-0">
          <section className="min-h-0">
            <VideoUpload
              session={session}
              onVideo={(meta, _fileUrl, backendSessionId) => {
                updateSession(session.id, (s) => ({
                  ...s,
                  video: meta,
                  backendSessionId: backendSessionId,
                  preprocessingStatus: "preprocessing",
                  title:
                    s.messages.length === 0 && s.title.startsWith("Session ")
                      ? meta.name.replace(/\.[^.]+$/, "")
                      : s.title,
                }));
              }}
              onPreprocessingUpdate={(status, errorMsg) => {
                updateSession(session.id, (s) => ({
                  ...s,
                  preprocessingStatus: status,
                  preprocessingError: errorMsg,
                }));
              }}
            />
          </section>
          <section className="min-h-0">
            <ChatPanel
              session={session}
              onSend={(userMsg, assistantMsg) => {
                updateSession(session.id, (s) => ({
                  ...s,
                  messages: [...s.messages, userMsg, assistantMsg],
                  title:
                    s.messages.length === 0 && s.title.startsWith("Session ")
                      ? userMsg.content.slice(0, 40)
                      : s.title,
                }));
              }}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
