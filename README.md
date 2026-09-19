# Sentinel Mesh

**Zero-trust security layer for networks of AI agents.**
*Identity is verified. Behavior is continuously evaluated.*

GoDaddy's Agent Name Service tells Sentinel **who** an agent is. Sentinel decides whether that
verified agent's **behavior** still deserves access, and it quarantines the agent when it doesn't.

- **Safety**: ANS identity, deterministic policy, Behavioral Risk Score, quarantine
- **Efficiency**: permission decay: just-in-time access that expires on its own
- **Visibility**: every decision is an immutable event; accountability reports per agent

## Quick start
```bash
brew install uv            # Python tooling (installs Python 3.12 for you)
make setup                 # backend + simulator + frontend deps, copies .env files
make backend               # terminal 1 → http://localhost:8000/docs
make sim                   # terminal 2 → simulator control API :8001
make frontend              # terminal 3 → http://localhost:3000
make backfill              # seed a week of history, then use the DEMO buttons
make test && make smoke    # checks
```

Docs: [CLAUDE.md](CLAUDE.md) (start here) · [Architecture](docs/ARCHITECTURE.md) · [API](docs/API.md) ·
[Demo script](docs/DEMO.md) · [Tasks](docs/TASKS.md)

Sponsors: GoDaddy ANS (identity), Google Gemini (behavioral analysis, advisory only).
