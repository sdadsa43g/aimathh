# Deployment

## Prerequisites

- Python 3.11+, Node 20+, Docker (for containerized runs).

## Local development

```bash
pip install -e .[dev]        # backend + test deps (or: pip install -e .)
make test                    # 115+ tests incl. adversarial benchmarks
make server                   # API on :8000  (uvicorn, reload)
cd apps/web && npm install && npm run dev   # UI on :5173 (proxies /v1 → :8000)
```

Configure providers (all optional) via `.env` — see `.env.example`:

```bash
cp .env.example .env
# OPENAI_API_KEY=... / ANTHROPIC_API_KEY=... / LOCAL_MODEL=... (Ollama)
```

Without keys the harness runs fully offline: heuristic planner + all
computational engines + MockProvider for plumbing tests.

## Docker Compose

```bash
docker compose up --build
# api → :8000, web → :4173 (preview server, static build)
```

Services: `api` (uvicorn, non-root, tmpfs `/tmp`), `web` (static build).
Sandbox and data volumes are mounted under `./data`.

## Production checklist

- [ ] Set `AIMATHH_ENV=prod`, strong CORS list, non-default ports as needed.
- [ ] Put the API behind TLS + auth (the API has no built-in user auth in v0.1).
- [ ] Enable egress firewall: model provider + `export.arxiv.org` +
      `api.openalex.org` only.
- [ ] Mount sandbox on tmpfs with size limits; run as non-root.
- [ ] Persist `./data` (SQLite memory DB, artifact store).
- [ ] Scrape `/v1/observability/stats` + structured JSON logs.

## CLI

```bash
aimathh research "Solve y'=-y and verify" --json
aimathh tool symbolic --args '{"op":"simplify","expr":"(x+1)^2"}'
aimathh verify --claim "E=mc^2" --dimensional "E = m*c^2" --symbols E=joule m=kg c=m/s
aimathh demo list && aimathh demo demo1_mechanics_derive_simulate
aimathh serve --port 8000
```
