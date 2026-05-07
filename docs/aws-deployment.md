# AWS Deployment Guide

This walks through deploying the API on a single EC2 instance with PostgreSQL on RDS and an optional S3 bucket for attachments. The setup is intentionally small so it fits inside the AWS Free Tier while still using the same services a larger deployment would.

## Architecture

```
       ┌──────────┐         ┌──────────────┐         ┌────────────┐
HTTPS  │  Client  │ ─────▶  │ EC2 (FastAPI)│ ─────▶  │  RDS       │
       └──────────┘         │   uvicorn    │  TCP    │  Postgres  │
                            └──────┬───────┘  5432   └────────────┘
                                   │
                                   │ s3:PutObject / GetObject (HTTPS)
                                   ▼
                            ┌──────────────┐
                            │   S3 Bucket  │
                            │  attachments │
                            └──────────────┘
```

## 1. Create the RDS Postgres database

1. RDS console → **Create database** → **Standard create** → **PostgreSQL**.
2. Template: **Free tier**.
3. Instance identifier: `task-manager-db`. Master user: `taskuser`. Password: store in a password manager.
4. Instance class: `db.t4g.micro`. Storage: 20 GB gp3.
5. **Public access**: No (use a bastion or session manager from inside the VPC).
6. Create a security group `task-manager-db-sg` allowing inbound `5432` only from the app security group below.
7. Initial database name: `tasks`.

The connection string the app will use:

```
postgresql+psycopg://taskuser:PASSWORD@<rds-endpoint>:5432/tasks
```

## 2. Create the S3 bucket (optional)

Only needed if you want the `/tasks/{id}/attachment` endpoint to actually upload files.

1. S3 console → **Create bucket**.
2. Name: `task-manager-attachments-<your-suffix>` (must be globally unique).
3. Region: same region as the EC2 instance.
4. Block all public access: **on**. The API uploads with the EC2 instance role; the bucket should never be public.
5. Default encryption: SSE-S3.

## 3. Create the IAM role for the EC2 instance

1. IAM → **Roles** → **Create role**.
2. Trusted entity: **AWS service** → **EC2**. (See `iam/ec2-trust-policy.json`.)
3. Attach a customer-managed policy built from `iam/s3-task-attachments-policy.json`. Replace `REPLACE_WITH_BUCKET_NAME` with the bucket from step 2.
4. Name the role `task-manager-app-role`.

This is least-privilege: the app can only `GetObject`/`PutObject`/`DeleteObject` under the `tasks/` prefix of the one bucket. No `*` resources.

## 4. Launch the EC2 instance

1. EC2 console → **Launch instance**.
2. AMI: Ubuntu 24.04 LTS. Type: `t3.micro`.
3. Key pair: create or reuse one.
4. Network: same VPC as the RDS instance.
5. Security group `task-manager-app-sg`:
   - Inbound `22` from your IP only (or use SSM Session Manager and skip this).
   - Inbound `80`/`443` from `0.0.0.0/0` if you put a load balancer in front; otherwise inbound `8000` from your IP for testing.
6. Advanced details → **IAM instance profile**: `task-manager-app-role`.

## 5. Install and run the app on the instance

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-pip git docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
# log out and back in for the docker group to take effect

git clone https://github.com/<you>/aws-task-manager-api.git
cd aws-task-manager-api

cat > .env <<'EOF'
DATABASE_URL=postgresql+psycopg://taskuser:PASSWORD@<rds-endpoint>:5432/tasks
APP_ENV=production
LOG_LEVEL=INFO
S3_ENABLED=true
AWS_REGION=us-west-2
S3_BUCKET_NAME=task-manager-attachments-<your-suffix>
EOF

docker build -t task-manager-api .
docker run -d --name api --env-file .env -p 8000:8000 task-manager-api
```

Note: do **not** put `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in `.env` on the instance. The instance role from step 3 supplies credentials automatically through the metadata service.

## 6. Smoke test

```bash
curl http://<public-ip>:8000/health
curl -X POST http://<public-ip>:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"first task","status":"pending"}'
```

## Hardening checklist before sharing the URL

- Put the EC2 instance behind an Application Load Balancer with an ACM certificate so traffic is HTTPS.
- Lock the app security group to the load balancer security group only.
- Enable RDS automatic backups and a maintenance window.
- Turn on CloudWatch agent on the EC2 instance and ship `docker logs api` to a log group.
- Rotate the database password through Secrets Manager and have the app read it on startup instead of from `.env`.

## Cost estimate (rough, us-west-2)

| Service | Size | Monthly |
|---|---|---|
| EC2 t3.micro | 1 instance, on-demand | ~$8 |
| RDS db.t4g.micro Postgres | 20 GB gp3, single AZ | ~$15 |
| S3 | 1 GB stored, 10k requests | <$1 |
| Data transfer | Light | <$1 |

Free Tier covers most of this for the first 12 months on a fresh account.
