import React, { useState, useRef } from 'react';
import { UploadCloud, X, FileText, Check, AlertCircle, Sparkles } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadFile: (file: File) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadFile,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleProcess = () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setTimeout(() => {
      onUploadFile(selectedFile);
      setIsUploading(false);
      onClose();
    }, 1000);
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

        <h2 className="text-xl font-black text-white tracking-tight mb-1">
          Upload Source Document
        </h2>
        <p className="text-xs text-zinc-400 mb-6">
          Ingest audited financial statements, annual reports, or compliance memos for neural claim extraction.
        </p>

        {/* Dropzone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-amber-400 bg-amber-400/10'
              : selectedFile
              ? 'border-emerald-500/80 bg-emerald-500/5'
              : 'border-[#28303e] hover:border-zinc-700 bg-[#181b22]'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && setSelectedFile(e.target.files[0])}
            className="hidden"
            accept=".pdf,.docx,.txt,.zip,.xlsx"
          />

          {selectedFile ? (
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
                <FileText className="w-6 h-6" />
              </div>
              <p className="text-sm font-bold text-white mb-1">{selectedFile.name}</p>
              <p className="text-xs font-mono text-zinc-400">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-xl bg-[#20252e] text-zinc-300 flex items-center justify-center mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-bold text-white mb-1">Click to browse or drag file here</p>
              <p className="text-xs text-zinc-500">Supports PDF, DOCX, TXT, ZIP up to 50MB</p>
            </div>
          )}
        </div>

        {/* Action button */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-white rounded-xl bg-zinc-800/40 hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!selectedFile || isUploading}
            onClick={handleProcess}
            className="px-5 py-2 text-xs font-extrabold uppercase tracking-wider text-black bg-[#F59E0B] hover:bg-[#d97706] disabled:bg-zinc-800 disabled:text-zinc-600 rounded-xl shadow-md transition-all cursor-pointer flex items-center gap-2"
          >
            {isUploading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                <span>Vectorizing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Ingest & Audit</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
