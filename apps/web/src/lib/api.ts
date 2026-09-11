/** Typed client for the AIMathH API. All calls use relative URLs so the
 *  Vite dev server proxies them to the backend (never direct localhost). */

export interface ToolSpec {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface ResearchResult {
  id: string;
  title: string;
  answer: string;
  equations: string[];
  verification: {
    status: string;
    evidence_level: string;
    methods: string[];
    checks: { name: string; status: string; detail: string }[];
    warnings: string[];
    discrepancy_report: string;
  };
  confidence: number;
  computations: unknown[];
  warnings: { code: string; message: string; severity: string }[];
  open_questions: string[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${path}: ${text.slice(0, 500)}`);
  }
  return (await r.json()) as T;
}

export const api = {
  health: () => req<{ status: string; version: string }>("/v1/health"),
  tools: () => req<{ tools: ToolSpec[]; stats: unknown }>("/v1/tools"),
  callTool: (name: string, args: Record<string, unknown>) =>
    req<{ ok: boolean; output: unknown; provenance: unknown }>(`/v1/tools/${name}/call`, {
      method: "POST",
      body: JSON.stringify({ args }),
    }),
  research: (query: string, max_steps = 10) =>
    req<ResearchResult>("/v1/research", {
      method: "POST",
      body: JSON.stringify({ query, max_steps }),
    }),
  verify: (claim: string, checks: unknown[]) =>
    req<{ status: string; evidence_level: string; checks: unknown[] }>("/v1/verify", {
      method: "POST",
      body: JSON.stringify({ claim, checks }),
    }),
  simulate: (body: Record<string, unknown>) => req<unknown>("/v1/simulations", {
    method: "POST",
    body: JSON.stringify(body),
  }),
  visualize: (body: Record<string, unknown>) =>
    req<{ figure: PlotlyFigure }>("/v1/visualize", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  scene3d: (body: Record<string, unknown>) => req<Scene3D>("/v1/scene3d", {
    method: "POST",
    body: JSON.stringify(body),
  }),
  constants: () => req<{ constants: { symbol: string; value: number; unit: string }[] }>("/v1/physics/constants", {
    method: "POST",
    body: JSON.stringify({ op: "list" }),
  }),
  artifacts: () => req<{ artifacts: { id: string; filename: string; kind: string; sha256: string }[] }>("/v1/artifacts"),
  jobs: () => req<{ jobs: { id: string; name: string; status: string; progress: number; message: string }[] }>("/v1/jobs"),
  submitJob: (name: string, kind: string, args: Record<string, unknown>) =>
    req<{ id: string }>("/v1/jobs", {
      method: "POST",
      body: JSON.stringify({ name, kind, args }),
    }),
  models: () => req<{ models: { name: string; provider: string; context_window: number }[] }>("/v1/models"),
};

export interface PlotlyFigure {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export interface Scene3D {
  kind: string;
  title: string;
  objects: Record<string, unknown>[];
}
