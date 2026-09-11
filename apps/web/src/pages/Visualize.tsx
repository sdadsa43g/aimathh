import { useState } from "react";
import { api, type Scene3D } from "../lib/api";
import Scene3DView from "../components/Scene3DView";

export default function Visualize() {
  const [expr, setExpr] = useState("sin(sqrt(x^2+y^2))");
  const [scene, setScene] = useState<Scene3D | null>(null);
  const [busy, setBusy] = useState(false);

  const build = async (kind: "surface" | "trajectory") => {
    setBusy(true);
    try {
      if (kind === "surface") {
        setScene(await api.scene3d({ kind: "surface", expr, n: 60, title: `z = ${expr}` }));
      } else {
        const sim = (await api.simulate({
          kind: "ode",
          rhs_exprs: ["sigma*(y-x)", "x*(rho-z)-y", "x*y-beta*z"],
          variables: ["x", "y", "z"],
          t_span: [0, 20],
          y0: [1, 1, 1],
          params: { sigma: 10, rho: 28, beta: 2.6667 },
        })) as { y: number[][] };
        const y = sim.y;
        const pts: number[][] = [];
        for (let i = 0; i < y[0].length; i += 2) pts.push([y[0][i], y[1][i], y[2][i]]);
        setScene(await api.scene3d({ kind: "trajectory", points: pts, title: "Lorenz attractor" }));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-4">
      <div className="panel p-4 grid gap-2">
        <div className="font-bold">3D scenes from computed data</div>
        <div className="flex gap-2 flex-wrap">
          <input className="input mono" style={{ maxWidth: 320 }} value={expr} onChange={(e) => setExpr(e.target.value)} />
          <button className="btn" onClick={() => build("surface")} disabled={busy}>Surface z = f(x,y)</button>
          <button className="btn" onClick={() => build("trajectory")} disabled={busy}>Lorenz trajectory</button>
        </div>
      </div>
      {scene && (
        <div className="panel p-4">
          <Scene3DView scene={scene} />
        </div>
      )}
    </div>
  );
}
