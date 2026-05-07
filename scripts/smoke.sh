#!/usr/bin/env bash
# Quick smoke test against a running API. Defaults to localhost:8000.
set -euo pipefail
HOST="${HOST:-http://localhost:8000}"

echo "GET $HOST/health"
curl -fsS "$HOST/health" | head -c 300; echo

echo "POST $HOST/tasks"
ID=$(curl -fsS -X POST "$HOST/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"title":"smoke task","description":"hello","status":"pending"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "created id=$ID"

echo "GET $HOST/tasks/$ID"
curl -fsS "$HOST/tasks/$ID"; echo

echo "PUT $HOST/tasks/$ID"
curl -fsS -X PUT "$HOST/tasks/$ID" \
  -H 'Content-Type: application/json' \
  -d '{"status":"in_progress"}'; echo

echo "DELETE $HOST/tasks/$ID"
curl -fsS -X DELETE "$HOST/tasks/$ID" -o /dev/null -w "%{http_code}\n"
