# Integration Tests

This directory contains API and service-boundary regressions for authenticated document processing, evidence retrieval, citations, workspaces, history, review records, OCR fallbacks, and query cancellation.

The test suite evolves with the product. Do not rely on this document for fixed test counts, coverage percentages, or release-status claims; run the suite to obtain the current result.

## Run locally

```bash
.venv/bin/python -m pytest -q tests/integration/
```

Run the full backend suite before release:

```bash
.venv/bin/python -m pytest -q tests/
```

## Test design

- Tests isolate external generation and vector dependencies where possible.
- Document, workspace, history, audit, and review tests verify owner isolation.
- Retrieval tests verify ready-document enforcement and workspace allow-lists.
- Citation tests verify source metadata and PDF-region behavior.
- OCR tests verify graceful operation when optional native OCR dependencies are absent.

## Configuration

The test configuration supplies local defaults and mocks for most external services. Do not place live provider credentials in test files or test environment defaults. Use `.env` only for intentional manual integration testing, and keep it ignored by Git.

For development workflow and release validation, see [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md) and [PROJECT_STATUS.md](../../PROJECT_STATUS.md).
