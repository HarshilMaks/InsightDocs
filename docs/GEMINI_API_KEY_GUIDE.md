# Getting Your Gemini API Key

InsightDocs uses **Google Gemini** for AI analysis. You need a free API key to get started.

---

## Steps (takes ~2 minutes)

1. **Go to** → [aistudio.google.com](https://aistudio.google.com)

2. **Sign in** with your Google account.

3. Click **"Get API key"** (top-left sidebar).

4. Click **"Create API key"** → select a Google Cloud project (or create one).

5. **Copy** the generated key (starts with `AIza...`).

6. **Paste it** into your `.env` file:
   ```
   GEMINI_API_KEY=AIzaSy...your-key-here
   ```

---

## Which model?

The default is `gemini-2.5-flash` — fast, capable, and free-tier friendly.

To use a different model, update `.env`:
```
GEMINI_MODEL=gemini-2.0-pro
```

---

## Free Tier Limits

| Model | Free Requests/min | Free Requests/day |
|---|---|---|
| gemini-2.5-flash | 15 | 1,500 |
| gemini-2.0-pro | 2 | 50 |

For most personal/demo use the free tier is sufficient.

---

## Keep your key safe

- **Never commit** `.env` to git — it is already in `.gitignore`.
- Rotate your key at [aistudio.google.com](https://aistudio.google.com) if you suspect it was leaked.
