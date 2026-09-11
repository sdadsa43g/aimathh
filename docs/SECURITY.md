# Security Model

Generated code is **untrusted**. The harness treats the model as a clever
adversary for security purposes.

## Enforcement layers

1. **Capability permissions.** Every tool declares required permissions from
   `{READ, WRITE, EXECUTE, NETWORK, INSTALL}`. Every call carries a
   `PermissionSet` grant; missing grants raise `PermissionDeniedError`.
   Network-requiring tools (literature) need explicit `NETWORK` grants —
   the API only grants it when `AIMATHH_ALLOW_NETWORK=true`.
2. **Sandboxed execution.** `execution/sandbox.py`:
   - fresh subprocess + fresh CWD under the sandbox root per run;
   - wall-time timeouts (default 120 s);
   - POSIX `RLIMIT_AS` memory caps (default 2048 MB), no core dumps;
   - minimal environment (`PATH`, `MPLBACKEND=Agg`, thread caps);
   - output truncation (200 kB) against log bombs;
   - extra-file writes confined to the sandbox (path-escape rejected).
3. **Secrets.** API keys only via environment / `.env` (see `.env.example`);
   never logged (structured logs carry run/tool IDs, not payloads).
4. **Reproducibility without exfiltration.** Provenance records inputs and
   dependency versions, never credentials.

## Known gaps (v0.1 — see LIMITATIONS.md)

- No OS-level network namespace / seccomp filter yet: the sandbox relies on
  policy (no NETWORK grant to sandboxed code paths) rather than kernel
  enforcement. **Do not run untrusted third-party prompts on sensitive hosts
  without container isolation** (use the provided Docker setup).
- No per-tenant authentication on the API; deploy behind an auth proxy for
  multi-user use.
- `INSTALL` permission exists in the model but no tool currently grants it;
  package installation inside the sandbox is not supported in v0.1.

## Deployment guidance

- Production: run `api` + `worker` in the Docker Compose setup as a
  non-root user, read-only repo mount, tmpfs sandbox volume, egress firewall
  allowing only your model provider + literature APIs.
- Rotate provider keys; scope them to least privilege.
