# InsightDocs Project Status

This is the concise reference for maintainers and AI assistants working in this repository. It records the supported product surface and points to authoritative documentation without duplicating implementation detail.

## Release position

InsightDocs is an evidence-first document application in release-ready maintenance state. The supported workflow is: upload a document, wait until it is ready, query one ready document or an explicit private Evidence Workspace, inspect citations, and use the retained Evidence Gate record for human review.

The repository does not claim automated truth, organization-wide sharing/RBAC, external connectors, document monitoring, evidence-packet export, or automated approval.

## Current guarantees

- Workspace retrieval is restricted to its explicit ready-document membership; it does not fall back to the full library.
- Documents, workspaces, history, audits, reviews, and retrieval are tenant- and owner-scoped.
- New PDF ingestions preserve precise multi-region citation geometry; older documents retain their stored single-region fallback until re-ingested.
- Browser Stop controls cancel active requests. The API avoids persisting a cancelled query when the disconnect is observed.
- Evidence Gate runs in shadow mode and retains reviewable claim-support records; human review remains the decision point.
- Sparse retrieval is supported for constrained deployments. API and worker must use compatible retrieval configuration.
- API startup is fail-closed when Alembic migrations fail.

## Authoritative references

| Need | Reference |
| --- | --- |
| Product scope and local start | [README.md](README.md) |
| Runtime and data-flow design | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Production deployment and migration procedure | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Environment variables | [.env.example](.env.example) |
| Public API index and generated schema | [docs/API.md](docs/API.md) and `/api/v1/docs` |
| Local setup | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| Development and validation | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| System summary | [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) |

## Change discipline

1. Keep ready-document enforcement, owner isolation, and workspace allow-lists intact.
2. Preserve migration/model alignment and do not bypass failed migrations with `alembic stamp` or manual version-table edits.
3. Keep credentials in ignored environment files, never in source, Markdown, tests intended for production, commits, or logs.
4. Run targeted tests for behavior changes, then the backend suite and frontend build before release.
5. Treat documents listed below as historical context, not implementation instructions.

## Historical records

The following files are retained only to explain prior audits, comparisons, or completed remediation. They are not current setup, architecture, deployment, security, or product guidance:

- `docs/ARCHITECTURE_COMPARISON.md`
- `docs/BYOK_AUDIT_REPORT.md`
- `docs/DATABASE_MIGRATIONS_EXPLAINED.md`
- `docs/ENV_AUDIT.md`
- `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`
- `docs/GEMINI_REPORT_ANALYSIS.md`

Use Git history for detailed prior change context. Do not add generic roadmap, status, or agent-policy documents unless they provide project-specific operational value.
