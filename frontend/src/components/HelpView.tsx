import React from 'react';
import { HelpCircle, Sparkles, BookOpen, Layers, ShieldCheck, CheckCircle2, ArrowRight } from 'lucide-react';

export const HelpView: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Document Ingestion & Neural Vectorization',
      desc: 'Upload PDF, Word, or plain text financial reports. The engine chunks text into 512-token segments and generates dense embeddings.',
    },
    {
      num: '02',
      title: 'Automated Claim Extraction',
      desc: 'Heuristic transformers scan the document for numerical claims, ARR metrics, operational expenses, and growth targets.',
    },
    {
      num: '03',
      title: 'Cross-Source Grounding & Verification',
      desc: 'Each extracted claim is verified against internal balance sheets, footnotes, and external source ledgers with confidence scores.',
    },
    {
      num: '04',
      title: 'Interactive Audit & Risk Flagging',
      desc: 'Ask complex audit questions in natural language, jump to exact citations, and export signed verification dossiers.',
    },
  ];

  return (
    <div id="help-guide-view" className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full font-sans text-zinc-200">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-white tracking-tight uppercase">
          NEURAL AUDIT PIPELINE GUIDE
        </h1>
        <p className="text-zinc-400 text-sm mt-1.5 font-normal">
          Learn how InsightDocs verifies claims, prevents hallucinations, and audits institutional documents.
        </p>
      </div>

      {/* Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {steps.map((step) => (
          <div key={step.num} className="bg-[#14171c] border border-[#262c37] rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <span className="text-3xl font-black font-mono text-amber-400/20 absolute top-4 right-4">
              {step.num}
            </span>
            <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/30 flex items-center justify-center text-amber-400 font-mono font-bold text-xs mb-4">
              {step.num}
            </div>
            <h3 className="text-base font-bold text-white mb-2">
              {step.title}
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              {step.desc}
            </p>
          </div>
        ))}
      </div>

      {/* FAQ / Guidance */}
      <div className="bg-[#14171c] border border-[#262c37] rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-extrabold uppercase tracking-wider text-white flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-amber-400" />
          <span>Frequently Asked Questions</span>
        </h3>

        <div className="space-y-3 text-xs">
          <div className="p-3.5 bg-[#181b22] rounded-xl border border-zinc-800">
            <h4 className="font-bold text-zinc-200 mb-1">How does BYOK work?</h4>
            <p className="text-zinc-400">
              When Bring-Your-Own-Key is enabled in BYOK Config, all audit queries use your personal Gemini API key stored in browser storage.
            </p>
          </div>

          <div className="p-3.5 bg-[#181b22] rounded-xl border border-zinc-800">
            <h4 className="font-bold text-zinc-200 mb-1">What triggers a [FLAGGED] status on a claim?</h4>
            <p className="text-zinc-400">
              Claims are flagged when numerical discrepancies, missing expense accruals, or ungrounded statistics are detected during cross-ledger checks.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
