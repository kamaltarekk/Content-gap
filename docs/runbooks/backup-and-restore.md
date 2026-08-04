# Backup and Restore Runbook (spec §31.6)

PostgreSQL is the source of truth; object storage (MinIO/S3) holds raw snapshots. Back up both.

## What to back up
- **Database** — all normalized + validated data, evidence spans, diagnoses, gaps, reports, cost
  ledger. Reports are immutable snapshots, so a DB backup preserves reproducible reports.
- **Object storage** — raw source snapshots referenced by `source_snapshots`. Keys are random; the
  DB holds the mapping.

## Database backup (daily, retained 30 days)
```bash
pg_dump --format=custom --no-owner \
  "postgresql://cgi:cgi@$DB_HOST:5432/cdga" \
  > "cdga-$(date -u +%Y%m%dT%H%M%SZ).dump"
```
Store the dump encrypted in a bucket separate from the primary storage bucket.

## Object storage backup
Mirror the storage bucket to a backup bucket (versioning enabled):
```bash
mc mirror --overwrite minio/cdga backup/cdga
```

## Restore (tested procedure)
1. Provision a clean PostgreSQL 17 instance with the `pgvector` extension.
2. Restore the schema + data:
   ```bash
   pg_restore --clean --if-exists --no-owner \
     -d "postgresql://cgi:cgi@$DB_HOST:5432/cdga" cdga-<timestamp>.dump
   ```
3. Confirm the migration head matches the application:
   ```bash
   cd backend && DATABASE_URL=postgresql+asyncpg://cgi:cgi@$DB_HOST:5432/cdga \
     uv run --python 3.12 alembic current   # must equal `alembic heads`
   ```
4. Restore the storage bucket from the backup bucket (`mc mirror backup/cdga minio/cdga`).
5. Smoke test: open a prior **approved report** and confirm its snapshot + evidence resolve
   unchanged (the §31.2 / §31.6 recovery check).

## Verification cadence
- Run a restore into a scratch environment monthly; record the run date here.
- A backup that has never been restored does not count as a backup.
