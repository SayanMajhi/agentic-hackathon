# NetCoop AI

Five agents exchange validatable evidence over a versioned protocol (`netcoop/1.0`), challenge one another, and publish one defensible JSON diagnosis of a campus network fault. The data is synthetic; nothing touches production infrastructure.

- Problem statement: [docs/problem_statement.pdf](docs/problem_statement.pdf)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Protocol and field reference: [PROTOCOL.md](PROTOCOL.md), with generated schemas in [schemas/](schemas/)
- Phase plan and status: [docs/STATUS.md](docs/STATUS.md)
- Current phase tasks: [docs/PHASE1_TASKS.md](docs/PHASE1_TASKS.md)
- Context for AI assistants: [CLAUDE.md](CLAUDE.md)

> **Status: skeleton.** The plumbing runs end to end: normalize → agents → Connectivity over REST → correlation → schema-valid report plus trace. The agents' diagnostic logic is still `TODO`, so every run currently ends in `insufficient_evidence`.

## Setup (3 commands)
```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

## Run
```bash
# terminal 1 — Connectivity agent as its own process
uvicorn connectivity_service.app:app --port 8001

# terminal 2 — diagnose a scenario (report -> reports/, trace -> traces/)
netcoop run scenarios/dev/sample_minimal.json
netcoop run scenarios/dev/sample_minimal.json --control   # Connectivity gets no peer findings
netcoop run scenarios/dev/sample_minimal.json --local     # in-process Connectivity (tests only)
```

After you change `netcoop/protocol/models.py`:
```bash
netcoop export-schemas      # regenerates schemas/*.json and the PROTOCOL.md field table; commit both
```

Dashboard (React + Vite):
```bash
cd dashboard && npm install && npm run gen:types && npm run dev
```

## Layout
| Path | What | Owner |
|---|---|---|
| `netcoop/protocol/` | models (source of truth), schema export, 0.9/2.x compat, agent cards | Lead |
| `netcoop/normalizer/` | generator adapter, aliases/units, windows, counter deltas | Backend 1 |
| `netcoop/agents/performance.py` | Performance agent | Backend 1 |
| `netcoop/agents/infrastructure.py` | Infrastructure agent | Backend 2 |
| `connectivity_service/` | Connectivity agent, separate FastAPI process | Backend 2 |
| `netcoop/orchestrator/` | bus, SQLite event log, registry, REST client, pipeline | Backend 2 |
| `netcoop/agents/correlation.py` | ranking, QUERY, `heuristic-v1`, decision gates | Lead |
| `netcoop/agents/reporting.py` | report-1.0 JSON and Markdown | Lead + Backend 2 |
| `netcoop/config/signatures-1.0.yaml` | global thresholds and signatures (versioned) | Backend 1 |
| `scenarios/` | topology, dev/held-out scenarios, `labels.json` (never read at runtime) | B2 / B1 / UI |
| `data/generator_raw/` | untouched organizer generator output and field mapping | Backend 1 |
| `examples/` | one valid message per type, 0.9 and 2.x samples, report samples | Lead |
| `dashboard/` | React + Vite UI, types generated from `schemas/` | UI |

## Git workflow
- Keep `main` green; CI runs `pytest` on every push and PR.
- Branch names: `m1/<role>-<topic>`. Open a PR, get one review, merge within about 2 hours.
- Only the Lead changes `netcoop/protocol/models.py`. Every schema change regenerates `schemas/` in the same PR.

## Limitations
_TODO before submission: synthetic data only; thresholds are heuristics, not calibrated; held-out evaluation results._
