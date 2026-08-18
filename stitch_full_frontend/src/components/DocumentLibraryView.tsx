import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Filter, 
  FileText, 
  FileArchive, 
  FileCode, 
  FileSpreadsheet, 
  Download, 
  Trash2, 
  Sparkles, 
  Eye, 
  ChevronRight, 
  ArrowUpRight, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Layers,
  Upload,
  Check,
  FolderArchive
} from 'lucide-react';
import { DocumentItem, DocumentStatus, DocumentType } from '../types';

interface DocumentLibraryViewProps {
  documents: DocumentItem[];
  searchQuery: string;
  onSelectDocument: (doc: DocumentItem) => void;
  onUploadClick: () => void;
  onDeleteDocument: (id: string) => void;
  onAddNewDocument: (file: File) => void;
}

export const DocumentLibraryView: React.FC<DocumentLibraryViewProps> = ({
  documents,
  searchQuery,
  onSelectDocument,
  onUploadClick,
  onDeleteDocument,
  onAddNewDocument,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isFilterMenuOpen, setIsFilterMenuOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Filter documents
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = 
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.typeLabel.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.contentSummary.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = filterType === 'all' || doc.type === filterType;
    const matchesStatus = filterStatus === 'all' || doc.status.toLowerCase() === filterStatus.toLowerCase();

    return matchesSearch && matchesType && matchesStatus;
  });

  const getDocIcon = (filename: string) => {
    if (filename.endsWith('.pdf')) {
      return <span className="material-symbols-outlined text-[20px] text-[#ffcc00] transition-colors">picture_as_pdf</span>;
    }
    if (filename.endsWith('.docx')) {
      return <span className="material-symbols-outlined text-[20px] text-[#ffcc00] transition-colors">description</span>;
    }
    if (filename.endsWith('.zip')) {
      return <span className="material-symbols-outlined text-[20px] text-[#ffcc00] transition-colors">folder_zip</span>;
    }
    return <span className="material-symbols-outlined text-[20px] text-[#ffcc00] transition-colors">draft</span>;
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'Completed':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-mono bg-white/10 text-white border border-white/20 status-badge">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 mr-2 shadow-[0_0_5px_#4ade80]" />
            Completed
          </span>
        );
      case 'Processing':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-mono bg-white/10 text-white border border-white/20 status-badge">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ffcc00] mr-2 animate-pulse shadow-[0_0_5px_#ffcc00]" />
            Processing
          </span>
        );
      case 'Pending':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-mono bg-white/5 text-white/80 border border-white/10 status-badge">
            <span className="w-1.5 h-1.5 rounded-full bg-white/50 mr-2" />
            Pending
          </span>
        );
      case 'Flagged':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-mono bg-red-500/10 text-red-300 border border-red-500/30 status-badge">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 mr-2 shadow-[0_0_5px_#f87171]" />
            Flagged
          </span>
        );
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      onAddNewDocument(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      onAddNewDocument(file);
    }
  };

  const handleDownload = (e: React.MouseEvent, doc: DocumentItem) => {
    e.stopPropagation();
    const element = document.createElement('a');
    const file = new Blob([doc.contentSummary], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = doc.name;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 lg:px-10 py-8 max-w-6xl mx-auto w-full font-sans text-white space-y-8">
      {/* Header & Actions matching exact reference */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Document Library
          </h2>
          <p className="text-base mt-2 max-w-xl text-white/80 font-normal">
            Manage and analyze your verified source documents through our advanced neural processing pipeline.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-4 shrink-0 relative">
          {/* Filter button & dropdown */}
          <div className="relative">
            <button
              id="btn-filter-toggle"
              onClick={() => setIsFilterMenuOpen(!isFilterMenuOpen)}
              className={`px-5 py-2.5 border border-white/10 rounded-xl transition-all duration-300 flex items-center gap-2 text-sm font-semibold glass-panel cursor-pointer ${
                filterType !== 'all' || filterStatus !== 'all'
                  ? 'bg-white/15 text-[#ffcc00] border-[#ffcc00]/40'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              <span className="material-symbols-outlined text-[18px]">filter_list</span>
              <span>Filter</span>
              {(filterType !== 'all' || filterStatus !== 'all') && (
                <span className="w-2 h-2 rounded-full bg-[#ffcc00] shadow-[0_0_6px_#ffcc00]" />
              )}
            </button>

            {isFilterMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-[#18181b]/95 backdrop-blur-xl border border-white/15 rounded-xl shadow-2xl p-4 z-30 flex flex-col gap-3 animate-fadeIn">
                <div>
                  <label className="text-[11px] font-bold uppercase tracking-wider text-white/60 block mb-1.5 font-mono">
                    File Type
                  </label>
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="w-full bg-black/50 border border-white/10 text-xs text-white rounded-lg p-2 outline-none focus:border-[#ffcc00]"
                  >
                    <option value="all">All File Types</option>
                    <option value="pdf">PDF Documents</option>
                    <option value="docx">Word (.docx)</option>
                    <option value="txt">Text (.txt)</option>
                    <option value="zip">Archive (.zip)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold uppercase tracking-wider text-white/60 block mb-1.5 font-mono">
                    Processing Status
                  </label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full bg-black/50 border border-white/10 text-xs text-white rounded-lg p-2 outline-none focus:border-[#ffcc00]"
                  >
                    <option value="all">All Statuses</option>
                    <option value="completed">Completed</option>
                    <option value="processing">Processing</option>
                    <option value="pending">Pending</option>
                    <option value="flagged">Flagged</option>
                  </select>
                </div>

                {(filterType !== 'all' || filterStatus !== 'all') && (
                  <button
                    onClick={() => {
                      setFilterType('all');
                      setFilterStatus('all');
                      setIsFilterMenuOpen(false);
                    }}
                    className="text-xs text-[#ffcc00] hover:underline text-left pt-1 font-mono cursor-pointer"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Upload Files Primary Button matching reference */}
          <button
            id="btn-upload-files"
            onClick={onUploadClick}
            className="px-5 py-2.5 bg-[#ffcc00] text-black text-sm rounded-xl transition-all duration-300 flex items-center gap-2 btn-glow border-beam-container hover:scale-105 transition-transform font-bold cursor-pointer shadow-lg shadow-amber-400/20"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
            <span>Upload Files</span>
          </button>
        </div>
      </div>

      {/* Drag & Drop Zone matching exact reference */}
      <div
        id="dropzone-upload-area"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative overflow-hidden border border-white/10 rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer glass-panel group retro-grid transition-all duration-500 hover:border-[#ffcc00]/50 ${
          isDragging ? 'border-[#ffcc00] bg-[#ffcc00]/5 scale-[1.005]' : ''
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          className="hidden"
          accept=".pdf,.docx,.txt,.zip,.xlsx,.csv"
        />

        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/40 pointer-events-none" />
        
        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-5 group-hover:scale-110 group-hover:bg-[#ffcc00]/10 transition-all duration-500 border border-white/10 group-hover:border-[#ffcc00]/30 relative z-10">
          <span className="material-symbols-outlined text-white/70 group-hover:text-[#ffcc00] text-3xl transition-colors duration-300">
            upload_file
          </span>
        </div>

        <h3 
          className="text-lg font-bold text-white relative z-10 group-hover:text-[#ffcc00] transition-colors"
          style={{ fontFamily: 'Space Grotesk, sans-serif' }}
        >
          Initialize Data Upload
        </h3>
        <p className="text-sm text-white/80 mt-2 relative z-10">
          Drag & drop neural weights, .pdf, .docx, or .txt (Max 50MB)
        </p>
      </div>

      {/* Document Table matching exact reference */}
      <div 
        id="documents-table-container"
        className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-2xl"
      >
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-white/10 bg-white/5 backdrop-blur-md font-mono text-white uppercase tracking-wider text-[11px] font-semibold">
          <div className="col-span-6 sm:col-span-5">Filename</div>
          <div className="col-span-3 sm:col-span-2">Type</div>
          <div className="hidden sm:block sm:col-span-2">Size</div>
          <div className="col-span-3 sm:col-span-2">Status</div>
          <div className="hidden sm:block sm:col-span-1 text-right">Actions</div>
        </div>

        {/* Table Rows */}
        <div className="divide-y divide-white/10 bg-transparent p-2" id="document-list">
          {filteredDocs.length === 0 ? (
            <div className="p-12 text-center text-white/60">
              <span className="material-symbols-outlined text-4xl mb-3 text-white/40 block">draft</span>
              <p className="text-sm font-medium">No documents match your filter criteria.</p>
              <button
                onClick={() => {
                  setFilterType('all');
                  setFilterStatus('all');
                }}
                className="mt-3 text-xs text-[#ffcc00] hover:underline font-mono cursor-pointer"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            filteredDocs.map((doc, index) => (
              <div
                key={doc.id}
                id={`doc-row-${doc.id}`}
                onClick={() => onSelectDocument(doc)}
                className="grid grid-cols-12 gap-4 px-6 py-4 items-center backdrop-blur-md bg-white/5 rounded-xl mb-2 hover:bg-white/10 transition-all duration-300 group cursor-pointer animate-fadeIn"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                {/* Filename & Icon */}
                <div className="col-span-6 sm:col-span-5 flex items-center gap-4 overflow-hidden">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center transition-all shrink-0">
                    {getDocIcon(doc.name)}
                  </div>
                  <span className="font-bold text-white truncate transition-colors group-hover:text-[#ffcc00]">
                    {doc.name}
                  </span>
                </div>

                {/* Type */}
                <div className="col-span-3 sm:col-span-2 text-white text-sm">
                  {doc.typeLabel}
                </div>

                {/* Size */}
                <div className="hidden sm:block sm:col-span-2 font-mono text-white text-[11px]">
                  {doc.size}
                </div>

                {/* Status */}
                <div className="col-span-3 sm:col-span-2">
                  {getStatusBadge(doc.status)}
                </div>

                {/* Actions */}
                <div className="hidden sm:flex sm:col-span-1 text-right justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <button
                    id={`btn-download-${doc.id}`}
                    onClick={(e) => handleDownload(e, doc)}
                    title="Download document summary"
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white hover:text-[#ffcc00] hover:bg-white/10 transition-colors cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[18px]">download</span>
                  </button>
                  <button
                    id={`btn-delete-${doc.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteDocument(doc.id);
                    }}
                    title="Delete document"
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white hover:text-red-400 hover:bg-red-400/10 transition-colors cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[18px]">delete</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-white/50 gap-2 font-mono">
        <p>Showing {filteredDocs.length} of {documents.length} verified repository documents</p>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-white/70">
            <span className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_#4ade80]" />
            Zero-Knowledge Neural Vector Ingestion Active
          </span>
        </div>
      </div>
    </div>
  );
};

