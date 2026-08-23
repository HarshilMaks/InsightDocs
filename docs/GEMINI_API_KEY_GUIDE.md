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

The default primary model is `gemini-3.6-flash`. If a key cannot access that exact model, InsightDocs discovers an accessible text-generation model for that key.

InsightDocs first tries the configured chain, then discovers a text-generation model accessible to that specific key if needed:

```
gemini-3.6-flash
gemini-3-flash-preview
then a compatible discovered model
```

To customize the initial order, update `.env`:
```
GEMINI_MODEL=gemini-3.6-flash
GEMINI_MODEL_FALLBACKS=gemini-3-flash-preview
```

---

## Limits

Gemini model availability and quotas vary by account, region, and current Google policy. The Settings page reports the model that is actually usable for the saved key; consult Google AI Studio for current limits.

The Settings page now shows whether your key is healthy, degraded to a fallback model, invalid, or
rate-limited, so you can see why BYOK is or is not enabled.

---

## Keep your key safe

- **Never commit** `.env` to git — it is already in `.gitignore`.
- Rotate your key at [aistudio.google.com](https://aistudio.google.com) if you suspect it was leaked.
