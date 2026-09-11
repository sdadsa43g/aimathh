import { useEffect, useState } from "react";
import { api, type PlotlyFigure } from "../lib/api";
import PlotView from "../components/PlotView";
import Equation from "../components/Equation";

export default function Lab() {
  // symbolic calculator
  const [expr, setExpr] = useState("sin(x)^2+cos(x)^2");
  const [symOut, setSymOut] = useState("");
  // simulation + plot
  const [fig, setFig] = useState<PlotlyFigure | null>(null);
  const [busy, setBusy] = useState(false);
  // dimensional check
  const [equation, setEquation] = useState("E = m*c^2");
  const [symbols, setSymbols] = useState('{"E":"joule","m":"kg","c":"m/s"}');
  const [dimOut, setDimOut] = useState("");
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);

  useEffect(() => {
    api.tools().then((t) => setTools(t.tools)).catch(() => {});
  }, []);

  const simplify = async () => {
    const r = await api.callTool("symbolic", { op: "simplify", expr, variables: ["x"] });
    setSymOut(JSON.stringify(r.output, null, 2));
  };

  const simulate = async () => {
    setBusy(true);
    try {
      const sim = (await api.simulate({
        kind: "ode",
        rhs_exprs: ["v", "-x"],
        variables: ["x", "v"],
        t_span: [0, 12.566],
        y0: [1, 0],
        energy_expr: "x^2/2+v^2/2",
      })) as { t: number[]; y: number[][] };
      const v = await api.visualize({
        kind: "ode",
        x: (sim.t as number[]).filter((_, i) => i % 2 === 0),
        y: (sim.y as number[][]).map((row) => row.filter((_, i) => i % 2 === 0)),
        variables: ["x", "v"],
        title: "Harmonic oscillator (live simulation)",
        save_png: false,
      });
      setFig(v.figure);
    } finally {
      setBusy(false);
    }
  };

  const checkDim = async () => {
    const r = await api.callTool("dimensional_check", { equation, symbols: JSON.parse(symbols) });
    setDimOut(JSON.stringify(r.output, null, 2));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="panel p-4 grid gap-2">
        <div className="font-bold">Symbolic calculator</div>
        <input className="input mono" value={expr} onChange={(e) => setExpr(e.target.value)} />
        <button className="btn w-fit" onClick={simplify}>Simplify via SymPy</button>
        {symOut && <pre className="json">{symOut}</pre>}
        <div className="text-sm opacity-80">Rendered:</div>
        <Equation latex="T = 2\pi\sqrt{\frac{L}{g}}" block />
      </div>
      <div className="panel p-4 grid gap-2">
        <div className="font-bold">Dimensional gate</div>
        <input className="input mono" value={equation} onChange={(e) => setEquation(e.target.value)} />
        <input className="input mono" value={symbols} onChange={(e) => setSymbols(e.target.value)} />
        <button className="btn w-fit" onClick={checkDim}>Check dimensions</button>
        {dimOut && <pre className="json">{dimOut}</pre>}
      </div>
      <div className="panel p-4 grid gap-2 lg:col-span-2">
        <div className="font-bold">Simulation → visualization (recomputed, never fabricated)</div>
        <button className="btn w-fit" onClick={simulate} disabled={busy}>
          {busy ? "Simulating…" : "Run oscillator + plot"}
        </button>
        {fig && <PlotView figure={fig} />}
      </div>
      <div className="panel p-4 lg:col-span-2">
        <div className="font-bold mb-2">Tool registry ({tools.length} tools)</div>
        <div className="grid md:grid-cols-2 gap-1 text-xs mono">
          {tools.map((t) => (
            <div key={t.name} className="py-0.5">
              <span className="text-cyan-300">{t.name}</span> — {t.description.slice(0, 90)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
