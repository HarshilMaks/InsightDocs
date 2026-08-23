# pgAdmin4 Reference

Use pgAdmin4 for read-only inspection and operational troubleshooting. Make schema changes through Alembic migrations, not through the pgAdmin query tool.

## Connection details

Use the PostgreSQL host, port, database, user, and password from your deployment environment or local `.env` file. Do not copy credentials into this document or commit them to Git.

## Safe checks

```sql
-- Applied Alembic revision
SELECT version_num FROM alembic_version;

-- Tables in the public schema
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Stored document-chunk columns, including citation geometry where migrated
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'document_chunks'
ORDER BY ordinal_position;
```

The current repository migration head is `d8e4f1a2b903`. Confirm the deployed source includes that migration before applying it.

## Operational rules

- Use `alembic upgrade head` to apply migrations.
- Do not manually alter application tables or modify `alembic_version` to bypass a mismatch.
- Do not reset, downgrade, or delete production data as a troubleshooting shortcut.
- Use read-only queries first when investigating an issue.

See [DEPLOYMENT.md](../DEPLOYMENT.md) for the release sequence and migration failure procedure.
