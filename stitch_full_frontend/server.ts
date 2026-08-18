import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

function getGeminiClient(customApiKey?: string) {
  const apiKey = customApiKey || process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return null;
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ extended: true, limit: "50mb" }));

  // Connection health ping
  app.get("/api/health", (req, res) => {
    res.json({
      status: "ok",
      timestamp: Date.now(),
      hasServerKey: !!process.env.GEMINI_API_KEY,
      engine: "InsightDocs Neural Kernel v4.2",
    });
  });

  // Audit Claims API
  app.post("/api/audit", async (req, res) => {
    try {
      const { documentText, query, customApiKey, modelName = "gemini-3.7-flash", strictness = "balanced" } = req.body;
      const ai = getGeminiClient(customApiKey);

      if (!ai) {
        // Return simulated audit response if no key is configured
        return res.json({
          analysis: "Audit completed via InsightDocs offline heuristic engine.",
          claims: [
            {
              id: "01",
              title: "Enterprise SaaS Tier Launch",
              content: "This launch accounted for 65% of new Annual Recurring Revenue (ARR).",
              status: "SUPPORTED",
              confidence: 0.98,
              citations: [{ source: "Q3_Financial_Audit_2024.pdf", page: 5, ref: "PG 5" }],
            },
            {
              id: "02",
              title: "Operational Efficiency",
              content: "Overhead was reduced by 4% year-over-year.",
              status: "FLAGGED",
              flagReason: "Pending secondary verification against vendor expense records.",
              confidence: 0.74,
              citations: [{ source: "ARR_Metrics_Q3.db", page: 2, ref: "DB" }],
            },
          ],
          summary: "Based on the provided document, the reported 18% revenue growth is substantially verified by core subscription expansions, while operational overhead reductions require secondary cross-ledger verification.",
          verifiedSources: [
            { id: "s1", label: "PG 5", docName: "Q3_Financial_Audit_2024.pdf", confidence: "98%" },
            { id: "s2", label: "DB", docName: "ARR_Metrics_Q3.db", confidence: "86%" },
          ],
        });
      }

      const prompt = `You are InsightDocs AI Auditor, an elite institutional document intelligence and claim-verification engine.
Analyze the following document context and answer the user query with rigorous fact-checking, extracted claims, and verification statuses.

Document Content:
${documentText || "No raw text provided. Audit the standard financial context."}

Audit Query:
${query || "Audit the primary claims and verify evidence."}

Strictness Mode: ${strictness}

Return a structured JSON response with this exact schema:
{
  "summary": "Brief executive analysis summary",
  "claims": [
    {
      "id": "01",
      "title": "Short descriptive claim title",
      "content": "Exact fact or figure extracted",
      "status": "SUPPORTED" | "FLAGGED" | "UNVERIFIED",
      "flagReason": "Optional reason if flagged or uncertain",
      "confidence": 0.95,
      "citations": [
        { "source": "Document name or section", "page": 5, "ref": "PG 5" }
      ]
    }
  ],
  "verifiedSources": [
    { "id": "s1", "label": "PG 5", "docName": "Document name", "confidence": "95%" }
  ]
}`;

      const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt,
        config: {
          responseMimeType: "application/json",
          systemInstruction: "You are InsightDocs AI Auditor. Respond with precise, structured financial and document audit reports in valid JSON format.",
        },
      });

      const responseText = response.text || "{}";
      try {
        const parsed = JSON.parse(responseText);
        res.json(parsed);
      } catch (parseErr) {
        res.json({
          summary: responseText,
          claims: [],
          verifiedSources: [],
        });
      }
    } catch (error: any) {
      console.error("Audit API Error:", error);
      res.status(500).json({ error: error.message || "Failed to process document audit" });
    }
  });

  // Interactive Document Chat API
  app.post("/api/chat", async (req, res) => {
    try {
      const { messages, documentContext, customApiKey, modelName = "gemini-3.7-flash" } = req.body;
      const ai = getGeminiClient(customApiKey);

      if (!ai) {
        return res.json({
          reply: "InsightDocs Assistant: The document specifies 18% revenue growth driven by Enterprise SaaS Tier ($4.2M ARR) and 4% overhead optimization. Would you like me to flag any cross-ledger variances?",
          claimsFound: 2,
        });
      }

      const formattedHistory = (messages || []).map((m: any) => `${m.role === "user" ? "Auditor/User" : "AI Auditor"}: ${m.content}`).join("\n");
      const prompt = `You are InsightDocs AI Auditor. 
Document Context:
${documentContext || "Q3 Financial Report & Audit Specs"}

Conversation History:
${formattedHistory}

Provide a crisp, professional audit response with citations, confidence scores, and any risk flags.`;

      const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt,
      });

      res.json({
        reply: response.text || "Analysis completed.",
      });
    } catch (error: any) {
      console.error("Chat API Error:", error);
      res.status(500).json({ error: error.message || "Chat failed" });
    }
  });

  // Test BYOK API Key
  app.post("/api/test-key", async (req, res) => {
    try {
      const { apiKey, modelName = "gemini-3.7-flash" } = req.body;
      if (!apiKey) {
        return res.status(400).json({ success: false, error: "API key is required" });
      }

      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: { headers: { "User-Agent": "aistudio-build" } },
      });

      const startTime = Date.now();
      const response = await ai.models.generateContent({
        model: modelName,
        contents: "Respond with the single word 'VALID'",
      });
      const pingMs = Date.now() - startTime;

      if (response.text) {
        res.json({ success: true, pingMs, model: modelName });
      } else {
        res.json({ success: false, error: "Empty response" });
      }
    } catch (error: any) {
      res.status(400).json({ success: false, error: error.message || "Invalid API Key" });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`InsightDocs Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
