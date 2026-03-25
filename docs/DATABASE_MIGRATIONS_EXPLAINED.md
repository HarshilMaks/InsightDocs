# Database Migrations & SQL Files - Complete Explanation

## Overview

InsightDocs uses **Alembic** (not raw SQL files) for database migrations. Here's why and how everything works.

---

## 🗂️ Current State: What You Have

### 1. **Alembic Migrations** (Active - Used by Project)

**Location**: `/home/harshil/insightdocs/alembic/versions/`

**Current Migrations**:
```
✅ 362ee7567368_initial_schema.py          (Applied)
✅ 73d37bbdf43d_add_byok_fields_to_user.py (Applied)
✅ 962463129f99_add_bounding_box_fields_to_chunks.py (Applied)
```

**These are the REAL migrations** that:
- Automatically run when you start the project
- Track schema changes in version control
- Can be rolled back if needed
- Are generated from your SQLAlchemy models

### 2. **Legacy SQL File** (Archived - NOT Used)

**Location**: `/home/harshil/insightdocs/scripts/legacy_migrations/001_add_ocr_tts_to_documents.sql`

**Content**:
```sql
-- Migration: Add OCR fields to documents table
ALTER TABLE documents ADD COLUMN is_scanned BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN ocr_confidence FLOAT;
```

**Status**: ⚠️ **This is OUTDATED and NOT USED**

**Why it exists**: This was created early in the project before we switched to Alembic. It's now archived for reference only.

---

## ❓ Why Don't We Use Raw SQL Files?

### The Problem with Raw SQL:
```sql
-- Example: manual.sql
ALTER TABLE users ADD COLUMN api_key VARCHAR(500);
```

❌ **Manual execution required**: You have to run it yourself  
❌ **No version tracking**: Can't tell what's been applied  
❌ **No rollback**: Can't undo changes easily  
❌ **Team coordination**: Others might miss running it  
❌ **Production risk**: Easy to forget or run twice  

### The Alembic Solution:
```python
# alembic/versions/73d37bbdf43d_add_byok_fields_to_user.py
def upgrade():
    op.add_column('users', sa.Column('gemini_api_key_encrypted', sa.String(500)))
    op.add_column('users', sa.Column('byok_enabled', sa.Boolean(), default=False))

def downgrade():
    op.drop_column('users', 'byok_enabled')
    op.drop_column('users', 'gemini_api_key_encrypted')
```

✅ **Auto-execution**: Runs on `alembic upgrade head`  
✅ **Version tracking**: Knows what's applied  
✅ **Rollback support**: Can run `downgrade()`  
✅ **Team-friendly**: Everyone gets same schema  
✅ **Production-safe**: Won't run twice  

---

## 📊 How Your Database Schema is Managed

### Current Workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  1. You update a SQLAlchemy model                          │
│     backend/models/schemas.py                              │
│                                                             │
│  2. Generate migration:                                    │
│     $ alembic revision --autogenerate -m "description"     │
│                                                             │
│  3. Review generated file in:                              │
│     alembic/versions/XXXXX_description.py                  │
│                                                             │
│  4. Apply to database:                                     │
│     $ alembic upgrade head                                 │
│                                                             │
│  5. Alembic tracks it in:                                  │
│     PostgreSQL table: alembic_version                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Example: What Happened When We Added Bounding Boxes

**Step 1**: Updated model
```python
# backend/models/schemas.py
class DocumentChunk(Base):
    # ... existing fields ...
    page_number = Column(Integer, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)
```

**Step 2**: Generated migration
```bash
$ alembic revision --autogenerate -m "add_bounding_box_fields_to_chunks"
# Created: alembic/versions/962463129f99_add_bounding_box_fields_to_chunks.py
```

**Step 3**: Applied to database
```bash
$ alembic upgrade head
# Output:
# INFO  [alembic.runtime.migration] Running upgrade 73d37bbdf43d -> 962463129f99, add_bounding_box_fields_to_chunks
```

**Step 4**: Alembic tracked it
```sql
-- Inside PostgreSQL:
SELECT * FROM alembic_version;
-- Result: 962463129f99 (current version)
```

---

## 🔧 How to Use pgAdmin4 with This Project

### Viewing Current Schema:

1. **Connect to PostgreSQL**:
   - Host: `localhost` (or your DB host)
   - Port: `5432`
   - Database: `insightdocs`
   - Username: `insightdocs`
   - Password: (from your `.env` file)

2. **Navigate**:
   ```
   Servers
     └── PostgreSQL 15
           └── Databases
                 └── insightdocs
                       └── Schemas
                             └── public
                                   └── Tables
   ```

3. **You Should See**:
   ```
   ✅ users
   ✅ documents
   ✅ document_chunks  (with bbox columns!)
   ✅ tasks
   ✅ queries
   ✅ alembic_version  (migration tracker)
   ```

### Checking Migration Status:

**In pgAdmin4 Query Tool**:
```sql
-- See current schema version
SELECT * FROM alembic_version;

-- Check if bbox columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'document_chunks';

-- Should show:
-- page_number | integer
-- bbox_x1 | double precision
-- bbox_y1 | double precision
-- bbox_x2 | double precision
-- bbox_y2 | double precision
```

---

## 🚨 IMPORTANT: Never Manually Edit Database Schema

### ❌ DON'T DO THIS:
```sql
-- In pgAdmin4 Query Tool
ALTER TABLE users ADD COLUMN new_field VARCHAR(100);
```

**Why not?**
1. Alembic won't know about the change
2. Your models won't match the database
3. Other developers won't get the change
4. Production will break when migrations run

### ✅ DO THIS INSTEAD:
```python
# 1. Update model in backend/models/schemas.py
class User(Base):
    # ... existing fields ...
    new_field = Column(String(100), nullable=True)

# 2. Generate migration
$ alembic revision --autogenerate -m "add_new_field_to_user"

# 3. Review the generated file

# 4. Apply it
$ alembic upgrade head
```

---

## 📚 Migration Commands Reference

```bash
# See current version
alembic current

# See migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 73d37bbdf43d

# Generate new migration (auto-detect changes)
alembic revision --autogenerate -m "description"

# Generate empty migration (manual changes)
alembic revision -m "description"
```

---

## 🗑️ What About That Legacy SQL File?

**Location**: `scripts/legacy_migrations/001_add_ocr_tts_to_documents.sql`

**Status**: **ARCHIVED - Do NOT run this manually**

**Why it's there**:
- Historical reference
- Shows what fields were added in early development
- Kept for documentation purposes

**What actually happened**:
- Those fields (is_scanned, ocr_confidence, etc.) were already added via the **initial Alembic migration** (`362ee7567368_initial_schema.py`)
- The SQL file was created before we committed to Alembic
- It's now outdated and superseded by Alembic migrations

**Should you run it in pgAdmin4?**
- ❌ **NO!** The fields already exist (added by Alembic)
- ❌ Running it would cause a "column already exists" error
- ✅ Just ignore it; it's for reference only

---

## 📋 Summary

| Aspect | Answer |
|--------|--------|
| **What manages schema?** | Alembic (not raw SQL files) |
| **Where are real migrations?** | `alembic/versions/*.py` |
| **Are they applied?** | Yes, all 3 migrations are applied |
| **What about .sql files?** | Legacy/archived, don't use them |
| **Can I use pgAdmin4?** | Yes, for viewing/querying only (not schema changes) |
| **How do I change schema?** | 1. Update model, 2. Generate migration, 3. Run `alembic upgrade head` |

---

## 🎯 TL;DR

1. **Alembic manages your database schema** (not manual SQL files)
2. **3 migrations are currently applied** and working correctly
3. **The legacy SQL file is archived** and should NOT be run manually
4. **Use pgAdmin4 for viewing/querying**, but schema changes go through Alembic
5. **Your database is up-to-date** with the latest schema (including bbox fields!)

---

**Questions?**
- Need to see current schema? → Use pgAdmin4
- Need to change schema? → Update model → Generate migration → Apply
- Confused about a field? → Check `backend/models/schemas.py`
- Want to see migration history? → `alembic history`
