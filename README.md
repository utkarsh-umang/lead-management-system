# lead-management-system

Lead Management System backend — CSV ingestion, canonical lead store, dedup,
and the enrichment ledger that the email finder (`ai-agents-service`) reads
and writes against. Design doc: `scalebrandslab/lms/Lead Management System.md`
in Obsidian.

Frontend lives in the separate `enlead` repo and talks to this API over
HTTP — this is not a monorepo.

## Quick start

1. **Install Task**: https://taskfile.dev/installation
2. **Install Docker** (for Postgres, Redis)

```bash
task env:create      # copy .env.example -> .env
task dev:infra        # start Postgres, Redis
task install           # poetry install
task migrate          # alembic upgrade head
task up                 # uvicorn on http://localhost:8000
```

Postgres runs on host port **5434** (not 5432) — this machine already runs
Postgres for other local projects on 5432/5433/54332.

## Task commands

| Task | Description |
|------|-------------|
| `task dev:infra` | Start Postgres, Redis (Docker) |
| `task dev:down` | Stop Docker infra |
| `task env:create` | Create `.env` from `.env.example` |
| `task install` | Install Python deps (Poetry) |
| `task migrate` | Run Postgres migrations |
| `task revision` | Create new Alembic migration |
| `task up` | Migrate + start uvicorn |
| `task test` | Run tests |
| `task lint` / `task format` | Ruff |

## Layout

```
.
├── .env.example
├── Taskfile.yml
├── docker-compose.yml   # Postgres, Redis
├── app/
│   ├── controllers/     # thin routers, delegate to services
│   ├── services/
│   ├── models/          # SQLModel tables (empty — no schema yet)
│   ├── schemas/         # Pydantic request/response
│   ├── db/               # engine/session (Postgres)
│   ├── cache/            # Redis client, graceful no-op if unavailable
│   └── core/             # config, auth contract, error handlers
├── migrations/           # Alembic (empty — no schema yet)
└── main.py
```

Status: **repo skeleton only** — no LMS schema/tables yet. That's the next
step, not this one.
