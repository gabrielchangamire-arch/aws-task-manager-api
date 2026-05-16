# aws-task-manager-api

A small task manager REST API written in Python with FastAPI. It runs on SQLite out of the box, swaps to PostgreSQL with a single env var, and has an optional S3 attachments path. I built it to practice backend fundamentals while keeping the path to AWS deployment clear: EC2 for the API, RDS for Postgres, and S3 for uploaded files.

[![ci](https://github.com/gabrielchangamire-arch/aws-task-manager-api/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielchangamire-arch/aws-task-manager-api/actions/workflows/ci.yml)

## What it does

- `GET  /health` – liveness + DB ping
- `POST /tasks` – create a task
- `GET  /tasks` – list tasks (paginated)
- `GET  /tasks/{id}` – fetch one
- `PUT  /tasks/{id}` – partial update (title, description, status)
- `DELETE /tasks/{id}` – delete
- `POST /tasks/{id}/attachment` – upload a file to S3 and link the key to the task

Tasks have a `status` enum (`pending`, `in_progress`, `done`), timestamps, and an optional S3 object key.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt   # macOS/Linux

cp .env.example .env
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive Swagger UI.

## Run with Docker (Postgres included)

```bash
docker compose up --build
```

This brings up Postgres and the API. `DATABASE_URL` inside the container points at the `db` service, so no extra setup needed.

## Tests

```bash
.venv/Scripts/python -m pytest -q
```

The S3 tests use [`moto`](https://github.com/getmoto/moto) so they run without real AWS credentials.

For the QA angle behind the endpoint coverage, see [`docs/API_TEST_STRATEGY.md`](docs/API_TEST_STRATEGY.md).

## API examples

```bash
# create
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"write proposal","description":"due friday","status":"pending"}'

# list
curl http://localhost:8000/tasks

# update status
curl -X PUT http://localhost:8000/tasks/<id> \
  -H 'Content-Type: application/json' \
  -d '{"status":"done"}'

# attachment (only works when S3_ENABLED=true and the bucket exists)
curl -X POST http://localhost:8000/tasks/<id>/attachment \
  -F file=@./notes.pdf
```

## Configuration

All config is env-driven via `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./tasks.db` | SQLAlchemy URL. Use `postgresql+psycopg://...` for Postgres or RDS. |
| `APP_ENV` | `development` | Tag for logs. |
| `LOG_LEVEL` | `INFO` | Root logger level. |
| `S3_ENABLED` | `false` | Turns the attachment endpoint on. |
| `AWS_REGION` | `us-west-2` | Region for the S3 client. |
| `S3_BUCKET_NAME` | (unset) | Bucket for attachments. |

When deployed on EC2 with an instance role attached, leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` unset; boto3 picks up role credentials automatically.

## Project layout

```
app/
  main.py            FastAPI app, lifespan, error handlers
  config.py          pydantic-settings, reads .env
  database.py        SQLAlchemy engine + session
  models.py          Task ORM model + status enum
  schemas.py         pydantic request/response models
  crud.py            DB read/write helpers
  routers/
    health.py
    tasks.py
  storage/
    s3.py            optional S3 attachment client
tests/                pytest, uses TestClient + moto
docs/                 AWS walkthrough + API test strategy
iam/                  least-privilege policy + EC2 trust policy
scripts/              run-dev.sh, smoke.sh
Dockerfile
docker-compose.yml
.github/workflows/ci.yml
```

## AWS architecture

See [`docs/aws-deployment.md`](docs/aws-deployment.md) for the full walkthrough. Short version:

- **EC2** runs the API container.
- **RDS Postgres** holds tasks. App connects via `DATABASE_URL`.
- **S3** holds attachment files. App writes under a `tasks/` prefix, scoped by IAM.
- **IAM** instance role grants only `s3:GetObject`/`PutObject`/`DeleteObject` on `tasks/*` of the one bucket — no wildcards, no console access.

## AWS pieces in the project

- **EC2** – running the containerized app on a t3.micro.
- **RDS / PostgreSQL** – managed Postgres connected via `DATABASE_URL`.
- **S3** – attachment storage with prefix-scoped IAM permissions.
- **IAM** – least-privilege policy + EC2 trust policy committed in `iam/`.
- **Security Groups** – app SG inbound from LB only, DB SG inbound from app SG only.
- **Environment-based config** – same image runs locally (SQLite, no S3) and in AWS (Postgres + S3) by changing env vars.
- **Docker** – multi-stage-friendly slim image, healthcheck, runs as non-root.
- **GitHub Actions CI** – lint/compile + tests on every push and PR.
- **Cloud debugging** – clear logs, structured handlers, `/health` checks DB connectivity.

## Design decisions

- **SQLite default, Postgres optional.** Lets a reviewer clone and run with one command. Prod uses Postgres because RDS gives us managed backups, point-in-time restore, and parameter groups.
- **S3 module is opt-in.** Disabled by default, returns `503` on the attachment route when off, so the API is fully usable without AWS creds.
- **No global state in routes.** `Depends(get_db)` per-request session, which is what FastAPI documents and what plays well with connection pooling on RDS.
- **UUID primary keys.** Easier to merge databases later and avoids leaking row counts.
- **One Pydantic model per shape.** Separate `TaskCreate`, `TaskUpdate`, and `TaskOut` so partial updates work cleanly and responses don't leak internal fields.

## What I learned building it

- pydantic-settings + a cached `get_settings()` makes test isolation easy: clear the cache, set env vars, re-read.
- FastAPI's lifespan context is a clean place to call `init_db()` — saves a CLI step in dev.
- `moto` is the right way to test boto3 code without an AWS account; mocking boto directly gets brittle fast.
- IAM policy writing is a real skill. Getting the `Resource` ARN right (`bucket/tasks/*` vs `bucket`) took longer than the code.
