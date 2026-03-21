# pgAdmin4 Quick Reference Guide

## 🔌 Connection Details

```
Host:     localhost (or your database host)
Port:     5432
Database: insightdocs
Username: insightdocs
Password: (check your .env file: POSTGRES_PASSWORD)
```

## 📊 What You'll Find

### Tables (6 total)

1. **alembic_version** - Tracks which migrations are applied
2. **users** - User accounts with BYOK encryption keys
3. **documents** - Uploaded files with OCR/TTS metadata
4. **document_chunks** - Text chunks with bounding boxes
5. **tasks** - Background job tracking
6. **queries** - RAG query history

## ✅ Verify Migrations

```sql
-- Check current schema version
SELECT * FROM alembic_version;

-- Expected: 962463129f99 (latest)
```

## 🔍 Useful Queries

### View all tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

### Check document_chunks schema
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'document_chunks'
ORDER BY ordinal_position;
```

### See BYOK-enabled users
```sql
SELECT email, byok_enabled, created_at 
FROM users 
WHERE byok_enabled = TRUE;
```

### Documents with bounding boxes
```sql
SELECT d.filename, COUNT(dc.id) as chunks_with_bbox
FROM documents d
JOIN document_chunks dc ON d.id = dc.document_id
WHERE dc.page_number IS NOT NULL
GROUP BY d.id, d.filename;
```

## ❌ DO NOT

- **Don't manually ALTER tables** (breaks Alembic tracking)
- **Don't DROP tables** (data loss + sync issues)
- **Don't run legacy SQL files** (already applied via Alembic)

## ✅ DO

- **View data** (read-only queries are safe)
- **Export data** (for backup/analysis)
- **Test queries** (before adding to API)
- **Monitor performance** (check slow queries)

## 🆘 Troubleshooting

### Can't connect?
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection settings in .env
cat .env | grep POSTGRES
```

### Missing tables?
```bash
# Apply migrations
cd /home/harshil/insightdocs
alembic upgrade head
```

### Want to reset database?
```bash
# WARNING: Destroys all data!
alembic downgrade base
alembic upgrade head
```

---

**Remember**: pgAdmin4 is for viewing and querying. Schema changes go through Alembic!
