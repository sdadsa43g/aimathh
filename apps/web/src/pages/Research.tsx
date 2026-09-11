import { useState } from "react";
import { api, type ResearchResult } from "../lib/api";
import VerifyBadge from "../components/VerifyBadge";

const EXAMPLES = [
  "Derive the period of a small-angle pendulum and verify it dimensionally.",
  "Solve y' = -y, y(0)=1 and cross-check symbolic vs numeric routes.",
  "Is E = m c dimensionally consistent? Check and explain.",
  "Optimize a 1-liter cylindrical can for minimum surface area.",
];

export default function Research() {
  const [query, setQuery] = useState(EXAMPLES[1]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await api.research(query, 8);
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-4">
      <div className="panel p-4 grid gap-2">
        <div className="font-bold">Research request</div>
        <textarea className="input" rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="flex gap-2 flex-wrap">
          <button className="btn" onClick={run} disabled={busy}>
            {busy ? "Researching…" : "Run MODEL → PLAN → COMPUTE → VERIFY"}
          </button>
          {EXAMPLES.map((ex) => (
            <button key={ex} className="btn text-xs" onClick={() => setQuery(ex)}>
              {ex.slice(0, 42)}…
            </button>
          ))}
        </div>
        {error && <pre className="json text-red-300">{error}</pre>}
      </div>
      {result && (
        <div className="panel p-4 grid gap-3">
          <div className="flex items-center gap-3">
            <VerifyBadge level={result.verification.evidence_level} />
            <span className="text-sm opacity-80">
              confidence {result.confidence.toFixed(2)} · {result.verification.methods.join(", ") || "no checks yet"}
            </span>
          </div>
          <pre className="whitespace-pre-wrap text-sm">{result.answer}</pre>
          {result.verification.checks.length > 0 && (
            <div>
              <div className="font-bold mb-1">Verification</div>
              {result.verification.checks.map((c, i) => (
                <div key={i} className="text-xs mono py-0.5">
                  [{c.status}] {c.name}: {c.detail.slice(0, 220)}
                </div>
              ))}
            </div>
          )}
          {result.warnings.length > 0 && (
            <div className="text-xs text-amber-300">
              {result.warnings.map((w, i) => (
                <div key={i}>⚠ {w.message.slice(0, 220)}</div>
              ))}
            </div>
          )}
          <details>
            <summary className="cursor-pointer text-sm opacity-80">
              computations ({result.computations.length})
            </summary>
            <pre className="json">{JSON.stringify(result.computations, null, 1).slice(0, 4000)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
