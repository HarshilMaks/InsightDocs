import React, { useState } from 'react';
import { Settings, Shield, Sliders, Database, Bell, Lock, Check } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [ocrEngine, setOcrEngine] = useState('tesseract-neural');
  const [extractTables, setExtractTables] = useState(true);
  const [crossCheckLedger, setCrossCheckLedger] = useState(true);
  const [auditAuditTrails, setAuditTrails] = useState(true);
  const [autoPurgeDays, setAutoPurgeDays] = useState('30');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div id="settings-view" className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full font-sans text-zinc-200">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight uppercase">
            AUDITOR PLATFORM SETTINGS
          </h1>
          <p className="text-zinc-400 text-sm mt-1.5 font-normal">
            Configure document ingestion rules, neural chunk size, and compliance retention.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="px-5 py-2.5 bg-[#F59E0B] hover:bg-[#d97706] text-black font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-md active:scale-95 transition-all cursor-pointer"
        >
          {saved ? 'Saved Changes!' : 'Save Settings'}
        </button>
      </div>

      <div className="space-y-6">
        {/* Extraction Settings */}
        <div className="bg-[#14171c] border border-[#262c37] rounded-2xl p-6 shadow-xl">
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-white mb-4 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-400" />
            <span>Document Ingestion & Neural Parsing</span>
          </h3>

          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-zinc-800/80">
              <div>
                <p className="font-semibold text-zinc-200">Automated Financial Table Extraction</p>
                <p className="text-xs text-zinc-400">Detect balance sheets and revenue tables and map them to structured JSON vectors.</p>
              </div>
              <input
                type="checkbox"
                checked={extractTables}
                onChange={(e) => setExtractTables(e.target.checked)}
                className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between py-2 border-b border-zinc-800/80">
              <div>
                <p className="font-semibold text-zinc-200">Cross-Ledger Verification Heuristics</p>
                <p className="text-xs text-zinc-400">Check numerical consistency across consecutive report pages automatically.</p>
              </div>
              <input
                type="checkbox"
                checked={crossCheckLedger}
                onChange={(e) => setCrossCheckLedger(e.target.checked)}
                className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-semibold text-zinc-200">OCR Engine Resolution</p>
                <p className="text-xs text-zinc-400">Multi-resolution neural layout analysis for scanned PDFs.</p>
              </div>
              <select
                value={ocrEngine}
                onChange={(e) => setOcrEngine(e.target.value)}
                className="bg-[#181b22] border border-[#282f3c] text-xs text-zinc-200 rounded-lg p-2 outline-none font-mono"
              >
                <option value="tesseract-neural">Neural Multimodal OCR (Highest Accuracy)</option>
                <option value="fast-ocr">Fast Text Stream (Lower Latency)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Security & Data Retention */}
        <div className="bg-[#14171c] border border-[#262c37] rounded-2xl p-6 shadow-xl">
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-white mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-amber-400" />
            <span>Compliance & Data Privacy</span>
          </h3>

          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-zinc-800/80">
              <div>
                <p className="font-semibold text-zinc-200">Cryptographic Audit Trails</p>
                <p className="text-xs text-zinc-400">Generate SHA-256 integrity hash seals for each audited document page.</p>
              </div>
              <input
                type="checkbox"
                checked={auditAuditTrails}
                onChange={(e) => setAuditTrails(e.target.checked)}
                className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-semibold text-zinc-200">Ephemeral Vector Retention</p>
                <p className="text-xs text-zinc-400">Automatically purge inactive temporary document embeddings.</p>
              </div>
              <select
                value={autoPurgeDays}
                onChange={(e) => setAutoPurgeDays(e.target.value)}
                className="bg-[#181b22] border border-[#282f3c] text-xs text-zinc-200 rounded-lg p-2 outline-none font-mono"
              >
                <option value="7">7 Days</option>
                <option value="30">30 Days (Recommended)</option>
                <option value="90">90 Days</option>
                <option value="never">Never Purge</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
