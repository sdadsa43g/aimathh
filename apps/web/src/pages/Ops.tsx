import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Ops() {
  const [jobs, setJobs] = useState<{ id: string; name: string; status: string; message: string }[]>([]);
  const [arts, setArts] = useState<{ id: string; filename: string; kind: string; sha256: string }[]>([]);
  const [models, setModels] = useState<{ name: string; provider: string; context_window: number }[]>([]);

  const refresh = () => {
    api.jobs().then((j) => setJobs(j.jobs)).catch(() => {});
    api.artifacts().then((a) => setArts(a.artifacts)).catch(() => {});
    api.models().then((m) => setModels(m.models)).catch(() => {});
  };
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, []);

  const submit = async () => {
    await api.submitJob("heat-demo", "simulate", { kind: "heat_1d", pde: { nx: 51, nt: 200, t_final: 0.2 } });
    refresh();
  };

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="panel p-4">
        <div className="font-bold mb-2">Models</div>
        {models.map((m) => (
          <div key={m.provider + m.name} className="text-xs mono py-0.5">
            {m.provider}/{m.name} · ctx {m.context_window}
          </div>
        ))}
      </div>
      <div className="panel p-4">
        <div className="font-bold mb-2">Jobs</div>
        <button className="btn mb-2" onClick={submit}>Submit heat-1D job</button>
        {jobs.map((j) => (
          <div key={j.id} className="text-xs mono py-0.5">
            [{j.status}] {j.name} — {j.message.slice(0, 60)}
          </div>
        ))}
        {jobs.length === 0 && <div className="text-xs opacity-60">no jobs yet</div>}
      </div>
      <div className="panel p-4">
        <div className="font-bold mb-2">Artifacts</div>
        {arts.slice(0, 20).map((a) => (
          <div key={a.id} className="text-xs mono py-0.5">
            <a className="text-cyan-300" href={`/v1/artifacts/${a.id}/download`}>{a.filename}</a>
            <span className="opacity-60"> · {a.kind} · {a.sha256.slice(0, 10)}</span>
          </div>
        ))}
        {arts.length === 0 && <div className="text-xs opacity-60">no artifacts yet</div>}
      </div>
    </div>
  );
}
