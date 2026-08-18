import React, { useState } from 'react';
import { Plus, X, FileText, Sparkles, ArrowRight, ShieldCheck, Layers } from 'lucide-react';
import { DocumentItem } from '../types';

interface NewAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  onSelectAndAudit: (doc: DocumentItem) => void;
  onOpenUpload: () => void;
}

export const NewAnalysisModal: React.FC<NewAnalysisModalProps> = ({
  isOpen,
  onClose,
  documents,
  onSelectAndAudit,
  onOpenUpload,
}) => {
  const [selectedDocId, setSelectedDocId] = useState<string>(documents[0]?.id || '');
  const [auditMode, setAuditMode] = useState<'financial' | 'compliance' | 'risk'>('financial');

  if (!isOpen) return null;

  const handleStart = () => {
    const doc = documents.find((d) => d.id === selectedDocId) || documents[0];
    if (doc) {
      onSelectAndAudit(doc);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg bg-[#14171c] border border-[#282f3c] rounded-2xl p-6 sm:p-8 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 p-1.5 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-xl font-black text-white tracking-tight mb-1 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <span>Launch New Analysis</span>
        </h2>
        <p className="text-xs text-zinc-400 mb-6">
          Select a document from your verified repository or upload a new file for deep claim-verification.
        </p>

        {/* Document Selection */}
        <div className="mb-5">
          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-300 block mb-2">
            Target Document
          </label>
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => setSelectedDocId(doc.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  selectedDocId === doc.id
                    ? 'bg-[#1f2530] border-amber-400 text-white'
                    : 'bg-[#181b22] border-[#282f3c] text-zinc-300 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileText className={`w-4 h-4 shrink-0 ${selectedDocId === doc.id ? 'text-amber-400' : 'text-zinc-400'}`} />
                  <span className="text-xs font-semibold truncate">{doc.name}</span>
                </div>
                <span className="text-[10px] font-mono text-zinc-400 shrink-0">{doc.size}</span>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => {
              onClose();
              onOpenUpload();
            }}
            className="text-xs text-amber-400 hover:underline mt-2 inline-flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Upload a different document</span>
          </button>
        </div>

        {/* Audit Mode */}
        <div className="mb-6">
          <label className="text-[11px] font-bold uppercase tracking-wider text-zinc-300 block mb-2">
            Audit Objective
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'financial', label: 'Financial Audit' },
              { id: 'compliance', label: 'Compliance Memo' },
              { id: 'risk', label: 'Risk & Overheads' },
            ].map((mode) => (
              <button
                key={mode.id}
                type="button"
                onClick={() => setAuditMode(mode.id as any)}
                className={`py-2 text-xs font-mono rounded-xl border transition-all ${
                  auditMode === mode.id
                    ? 'bg-amber-400 text-black font-bold border-amber-400 shadow-md'
                    : 'bg-[#181b22] border-[#282f3c] text-zinc-400 hover:text-white'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        {/* Start Button */}
        <button
          type="button"
          onClick={handleStart}
          className="w-full bg-[#F59E0B] hover:bg-[#d97706] text-black font-extrabold text-xs uppercase tracking-wider py-3 px-4 rounded-xl flex items-center justify-center gap-2 shadow-md shadow-amber-500/10 active:scale-98 transition-all cursor-pointer"
        >
          <span>INITIALIZE AUDIT ASSISTANT</span>
          <ArrowRight className="w-4 h-4 stroke-[3]" />
        </button>
      </div>
    </div>
  );
};
