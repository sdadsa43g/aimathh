import { useEffect, useState } from "react";
import Research from "./pages/Research";
import Lab from "./pages/Lab";
import Visualize from "./pages/Visualize";
import Ops from "./pages/Ops";
import { api } from "./lib/api";

const TABS = ["Research", "Lab", "Visualize", "Ops"] as const;

export default function App() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Research");
  const [health, setHealth] = useState("…");

  useEffect(() => {
    api.health()
      .then((h) => setHealth(`${h.status} v${h.version}`))
      .catch(() => setHealth("API unreachable — start `make server`"));
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-4 grid gap-4">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold">AIMathH <span className="text-cyan-300">Research Harness</span></h1>
          <div className="text-xs opacity-70">MODEL → PLAN → COMPUTE → VERIFY → CROSS-CHECK → CRITIQUE → PRESENT</div>
        </div>
        <div className="text-xs mono">API: {health}</div>
      </header>
      <nav className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            className={`btn ${tab === t ? "outline outline-1 outline-cyan-300" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>
      <main>
        {tab === "Research" && <Research />}
        {tab === "Lab" && <Lab />}
        {tab === "Visualize" && <Visualize />}
        {tab === "Ops" && <Ops />}
      </main>
      <footer className="text-xs opacity-60">
        Every number in this UI comes from an executed tool call. Unchecked claims are labeled UNVERIFIED by construction.
      </footer>
    </div>
  );
}
