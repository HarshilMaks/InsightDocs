# Virtual Environment Usage Guide

## Quick Reference

### Activating the Virtual Environment

**Linux/Mac:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### Deactivating
```bash
deactivate
```

---

## Common Commands

### Installing Packages
```bash
# Activate first
source .venv/bin/activate

# Install from requirements.txt
uv pip install -r requirements.txt

# Install development dependencies
uv pip install -r requirements-dev.txt

# Install a single package
uv pip install package-name
```

### Running the Application
```bash
# Activate environment
source .venv/bin/activate

# Start API server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# OR use Makefile (automatically activates .venv)
make run-backend
```

### Running Celery Worker
```bash
# Activate environment
source .venv/bin/activate

# Start Celery worker
celery -A backend.workers.celery_app worker --loglevel=info

# OR use Makefile
make run-worker
```

### Checking Installed Packages
```bash
source .venv/bin/activate
uv pip list
```

---

## Pro Tips

### 1. Always Activate Before Working
Make it a habit to activate the virtual environment when you start working:
```bash
cd /home/harshil/InsightDocs
source .venv/bin/activate
```

### 2. Use Makefile Commands
The Makefile commands automatically handle .venv activation:
```bash
make run-backend    # Runs with .venv activated
make run-worker     # Runs with .venv activated
make install        # Installs with .venv activated
```

### 3. Check if Environment is Active
When activated, you'll see `(.venv)` in your terminal prompt:
```bash
(.venv) harshil@LEGIONOFLEGEND:~/InsightDocs$
```

### 4. Multiple Terminal Windows
Each terminal window needs its own activation:
```bash
# Terminal 1
source .venv/bin/activate
make run-backend

# Terminal 2 (separate terminal)
source .venv/bin/activate
make run-worker
```

---

## Troubleshooting

### "Command not found" errors
**Problem:** Running commands without activating .venv
**Solution:** Always activate first:
```bash
source .venv/bin/activate
uvicorn backend.api.main:app --reload
```

### Module import errors
**Problem:** Packages not installed in .venv
**Solution:** Activate and install:
```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Wrong Python version
**Problem:** Using system Python instead of .venv Python
**Solution:** Verify you're using .venv Python:
```bash
source .venv/bin/activate
which python  # Should show: /home/harshil/InsightDocs/.venv/bin/python
```

---

## Docker vs Local Development

### When to Use Docker
- ✅ Full system testing
- ✅ Production-like environment
- ✅ All services together
- ❌ No .venv activation needed

```bash
docker-compose up -d
# Everything runs in containers
```

### When to Use .venv (Local)
- ✅ Fast development iterations
- ✅ Debugging with IDE
- ✅ Quick code changes
- ✅ Direct access to Python debugger

```bash
source .venv/bin/activate
uvicorn backend.api.main:app --reload
```

---

## IDE Configuration

### VS Code
Add to `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```

### PyCharm
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select: `/home/harshil/InsightDocs/.venv/bin/python`

---

## Summary

**Always remember:**
1. Activate .venv before running Python commands
2. Use `make` commands for convenience
3. Each terminal needs its own activation
4. Deactivate when switching projects

**Quick Start:**
```bash
cd /home/harshil/InsightDocs
source .venv/bin/activate
make run-backend
```
