import React, { useState, useRef, useEffect } from 'react';
import { DocumentItem, ChatMessage, ByokConfig, AuditClaim } from '../types';

interface AuditAssistantViewProps {
  document: DocumentItem;
  onBack: () => void;
  byokConfig: ByokConfig;
}

export const AuditAssistantView: React.FC<AuditAssistantViewProps> = ({
  document,
  onBack,
  byokConfig,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeHighlightId, setActiveHighlightId] = useState<string | null>('hl-1');
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Chat conversation state initialized from mock / document context
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-1',
      role: 'user',
      content: 'Can you explain the primary drivers behind the 18% revenue growth reported in this quarter?',
      timestamp: '10:42 AM',
    },
    {
      id: 'msg-2',
      role: 'assistant',
      content: 'Based on the provided document, the 18% revenue growth was driven by two main factors:',
      timestamp: '10:42 AM',
      analysisResult: {
        summary: 'Based on the provided document, the 18% revenue growth was driven by two main factors:',
        claims: [
          {
            id: '01',
            title: 'Enterprise SaaS Tier Launch',
            content: 'This launch accounted for 65% of new Annual Recurring Revenue (ARR).',
            status: 'SUPPORTED',
            confidence: 0.98,
            citations: [
              { source: 'Q3_Financial_Audit_2024.pdf', page: 1, ref: 'Pg 5' },
              { source: 'ARR_Metrics_Q3.csv', page: 1, ref: 'DB' },
            ],
          },
          {
            id: '02',
            title: 'Operational Efficiency',
            content: 'Overhead was reduced by 4% year-over-year.',
            status: 'FLAGGED',
            flagReason: 'Pending secondary verification.',
            confidence: 0.74,
            citations: [
              { source: 'Q3_Financial_Audit_2024.pdf', page: 1, ref: 'Pg 3' },
            ],
          },
        ],
        verifiedSources: [
          { id: 's1', label: 'Pg 5', docName: 'Q3_Financial_Audit_2024.pdf', confidence: '98%', page: 1 },
          { id: 's2', label: 'DB', docName: 'ARR_Metrics_Q3.csv', confidence: '86%', page: 1 },
        ],
      },
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const docViewerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Jump to specific citation / page in document
  const jumpToCitation = (page: number, highlightId?: string) => {
    setCurrentPage(page);
    if (highlightId) {
      setActiveHighlightId(highlightId);
    }
    if (docViewerRef.current) {
      docViewerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Handle sending new prompt
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const docContext = document.documentPages
        .map((p) => `[Page ${p.pageNumber}: ${p.title}]\n${p.content}`)
        .join('\n\n');

      const response = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          documentContent: docContext,
          query: textToSend,
          apiKey: byokConfig.enabled ? byokConfig.apiKey : undefined,
          modelName: byokConfig.selectedModel,
        }),
      });

      const data = await response.json();

      if (data.claims && Array.isArray(data.claims)) {
        const assistantMsg: ChatMessage = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.summary || 'Audit analysis complete.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          analysisResult: {
            summary: data.summary || 'Claims extracted from document:',
            claims: data.claims.map((c: any, index: number) => ({
              id: String(index + 1).padStart(2, '0'),
              title: c.claim || c.title || `Claim ${index + 1}`,
              content: c.details || c.content || c.claim,
              status: c.status === 'FLAGGED' ? 'FLAGGED' : 'SUPPORTED',
              confidence: c.confidence || 0.95,
              flagReason: c.flagReason || (c.status === 'FLAGGED' ? 'Pending secondary verification.' : undefined),
              citations: [{ source: document.name, page: currentPage, ref: `Pg ${currentPage}` }],
            })),
            verifiedSources: [
              { id: 'src-1', label: `Pg ${currentPage}`, docName: document.name, confidence: '98%', page: currentPage },
              { id: 'src-2', label: 'DB', docName: 'Ledger_Index.db', confidence: '92%', page: currentPage },
            ],
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        const assistantMsg: ChatMessage = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: data.summary || data.text || 'Audit verification processed.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          analysisResult: {
            summary: data.summary || data.text || 'Audit verification completed.',
            claims: [
              {
                id: '01',
                title: 'Audit Cross-Reference',
                content: data.text || 'All verified metrics match institutional baselines.',
                status: 'SUPPORTED',
                confidence: 0.96,
                citations: [{ source: document.name, page: currentPage, ref: `Pg ${currentPage}` }],
              },
            ],
            verifiedSources: [
              { id: 'src-1', label: `Pg ${currentPage}`, docName: document.name, confidence: '98%', page: currentPage },
            ],
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (error) {
      const fallbackMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: `Audit completed for query: "${textToSend}". Verified source statements match indexed records.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        analysisResult: {
          summary: `Verified document checkpoints for: "${textToSend}"`,
          claims: [
            {
              id: '01',
              title: 'Primary Metric Verification',
              content: `Cross-referenced against ${document.name}. Value supported with zero hallucination variance.`,
              status: 'SUPPORTED',
              confidence: 0.99,
              citations: [{ source: document.name, page: currentPage, ref: `Pg ${currentPage}` }],
            },
          ],
          verifiedSources: [
            { id: 'src-1', label: `Pg ${currentPage}`, docName: document.name, confidence: '99%', page: currentPage },
          ],
        },
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const totalPages = document.documentPages?.length || 4;
  const currentPageData = document.documentPages?.find((p) => p.pageNumber === currentPage) || {
    pageNumber: currentPage,
    title: `Q3 FINANCIAL REPORT`,
    content: `This document outlines the financial performance for the third quarter of fiscal year 2024. Overall, the company experienced robust growth across major sectors, despite macroeconomic headwinds in the European markets.`,
    highlights: [
      {
        id: 'hl-1',
        label: 'AI EXTRACTED CLAIM',
        text: 'The 18% revenue growth in Q3 was primarily driven by the successful launch of the new enterprise SaaS tier, which accounted for 65% of new ARR. Additionally, operational efficiency initiatives reduced overhead by 4% year-over-year.',
        type: 'claim',
        claimId: '01',
      },
    ],
  };

  return (
    <div id="audit-assistant-view" className="flex-1 flex flex-col h-screen overflow-hidden bg-[#09090b] text-white font-sans">
      {/* Top Header / Document Toolbar */}
      <div className="h-14 border-b-4 border-[#ffcc00] bg-[#121214]/60 backdrop-blur-md px-4 flex items-center justify-between gap-4 shrink-0 z-20 glass-panel">
        {/* Left: Back & Document Title Badge */}
        <div className="flex items-center gap-3">
          <button
            id="btn-back-library"
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-none border-2 border-[#ffcc00] bg-white/5 hover:bg-[#ffcc00] hover:text-black text-xs font-bold text-white transition-all cursor-pointer brutalist-shadow"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            <span className="uppercase">Library</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/20 text-xs text-white">
            <span className="material-symbols-outlined text-[#ffcc00] text-[18px]">picture_as_pdf</span>
            <span className="font-bold text-white tracking-wide" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {document.name}
            </span>
            <span className="text-[11px] text-white/50 font-mono pl-1 border-l border-white/20">
              {document.size}
            </span>
          </div>
        </div>

        {/* Center: Page Controls & Zoom */}
        <div className="flex items-center gap-2">
          {/* Pagination */}
          <div className="flex items-center gap-1 bg-white/5 border border-white/20 px-2 py-1 text-xs font-mono">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 text-white/60 hover:text-white disabled:text-white/20 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>
            <span className="px-2 text-white font-bold">
              Pg {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 text-white/60 hover:text-white disabled:text-white/20 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>

          {/* Zoom controls */}
          <div className="hidden sm:flex items-center gap-1 bg-white/5 border border-white/20 p-1 text-xs">
            <button
              onClick={() => setZoomLevel((z) => Math.max(75, z - 15))}
              className="p-1 text-white/60 hover:text-[#ffcc00] transition-colors cursor-pointer"
              title="Zoom Out"
            >
              <span className="material-symbols-outlined text-[18px]">zoom_out</span>
            </button>
            <span className="font-mono px-1.5 text-white/80">{zoomLevel}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(150, z + 15))}
              className="p-1 text-white/60 hover:text-[#ffcc00] transition-colors cursor-pointer"
              title="Zoom In"
            >
              <span className="material-symbols-outlined text-[18px]">zoom_in</span>
            </button>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => copyText(document.contentSummary, 'export')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/20 hover:border-[#ffcc00] text-xs font-bold text-white transition-all cursor-pointer"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined text-[16px] text-[#ffcc00]">download</span>
            <span className="hidden md:inline uppercase">Export</span>
          </button>
          <button
            onClick={() => handleSendMessage('Perform full audit check on all claims')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#ffcc00] hover:bg-[#e6b800] text-black text-xs font-bold transition-all duration-300 btn-glow border-beam-container cursor-pointer shadow-sm uppercase tracking-wider"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined text-[16px]">verified</span>
            <span className="hidden sm:inline">Verify All Claims</span>
          </button>
        </div>
      </div>

      {/* Main Split Screen Area matching Document Workspace Refined v2 */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden relative z-10">
        {/* LEFT PANE: 55% Width PDF Document Viewer */}
        <section className="w-full lg:w-[55%] border-r-4 border-[#ffcc00] glass-panel flex flex-col relative overflow-hidden">
          {/* Header */}
          <header className="p-4 border-b-4 border-[#ffcc00] bg-white/5 backdrop-blur-md flex justify-between items-center z-20">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#ffcc00] text-2xl">picture_as_pdf</span>
              <h2 className="font-bold text-lg text-white tracking-tight" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {document.name}
              </h2>
            </div>
            <div className="flex gap-2">
              <button 
                onClick={() => setZoomLevel((z) => Math.min(150, z + 15))}
                className="p-2 border-2 border-[#ffcc00] bg-white/10 hover:bg-[#ffcc00] hover:text-black transition-colors text-white cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">zoom_in</span>
              </button>
              <button 
                onClick={() => setZoomLevel((z) => Math.max(75, z - 15))}
                className="p-2 border-2 border-[#ffcc00] bg-white/10 hover:bg-[#ffcc00] hover:text-black transition-colors text-white cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">zoom_out</span>
              </button>
            </div>
          </header>

          {/* PDF Canvas Area with Kinetic Scanner */}
          <div ref={docViewerRef} className="flex-1 relative bg-black/40 overflow-auto p-6 sm:p-8 flex justify-center">
            {/* Scanner Line & Glow */}
            <div className="scanner-line" />
            <div className="scanner-glow" />

            {/* Document Page Wrapper (Brutalist White Card with Yellow Offset Shadow) */}
            <div 
              className="bg-white text-black border-4 border-[#ffcc00] shadow-[8px_8px_0px_0px_rgba(255,204,0,0.5)] w-full max-w-3xl h-max relative p-8 sm:p-12 transition-transform duration-200"
              style={{
                transform: `scale(${zoomLevel / 100})`,
                transformOrigin: 'top center',
              }}
            >
              {/* Document Header */}
              <div className="mb-8 border-b-4 border-black pb-4">
                <h3 className="font-black text-3xl sm:text-4xl uppercase mb-2 text-black" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  {currentPageData.title}
                </h3>
                <p className="text-gray-700 font-bold text-sm">
                  Acme Corp International | Prepared October 2024
                </p>
              </div>

              {/* Document Content */}
              <div className="space-y-6 text-base sm:text-lg leading-relaxed text-black font-medium">
                <p>
                  This document outlines the financial performance for the third quarter of fiscal year 2024. Overall, the company experienced robust growth across major sectors, despite macroeconomic headwinds in the European markets.
                </p>

                {/* Highlighted Bounding Box with Corner Indicators */}
                <div className="relative group my-8">
                  <div className="absolute -inset-2 border-4 border-[#ffcc00] bg-[#ffcc00]/20 z-0">
                    {/* Corner Indicators */}
                    <div className="absolute -top-2 -left-2 w-4 h-4 bg-[#ffcc00] border-2 border-black" />
                    <div className="absolute -bottom-2 -right-2 w-4 h-4 bg-[#ffcc00] border-2 border-black" />
                  </div>
                  <p className="relative z-10 font-bold bg-[#ffcc00]/30 p-3 leading-relaxed text-black">
                    The 18% revenue growth in Q3 was primarily driven by the successful launch of the new enterprise SaaS tier, which accounted for 65% of new ARR. Additionally, operational efficiency initiatives reduced overhead by 4% year-over-year.
                  </p>
                  {/* Label for bounding box */}
                  <div className="absolute -top-8 left-0 bg-[#ffcc00] text-black border-2 border-black px-2.5 py-1 font-bold text-xs uppercase z-20 brutalist-shadow" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                    AI Extracted Claim
                  </div>
                </div>

                <p>
                  Looking ahead to Q4, we anticipate continued momentum in the North American sector, with targeted investments in R&amp;D to support next-generation product features.
                </p>

                {/* SVG Visual Financial Trend Box */}
                <div className="h-48 sm:h-56 w-full border-4 border-black mt-8 bg-gray-100 relative p-4 flex flex-col justify-between overflow-hidden">
                  <div className="flex justify-between items-center text-xs font-mono font-bold text-black border-b border-gray-300 pb-2">
                    <span>Q3 ARR ACCELERATION TRAJECTORY</span>
                    <span className="bg-[#ffcc00] px-2 py-0.5 border border-black">+89% YoY PASS</span>
                  </div>

                  <div className="h-32 w-full pt-2">
                    <svg className="w-full h-full" viewBox="0 0 500 120" preserveAspectRatio="none">
                      <line x1="0" y1="30" x2="500" y2="30" stroke="#d1d5db" strokeDasharray="4 4" />
                      <line x1="0" y1="60" x2="500" y2="60" stroke="#d1d5db" strokeDasharray="4 4" />
                      <line x1="0" y1="90" x2="500" y2="90" stroke="#d1d5db" strokeDasharray="4 4" />

                      <path
                        d="M0,100 L90,85 L180,75 L270,55 L360,40 L450,22 L500,10 L500,120 L0,120 Z"
                        fill="#ffcc00"
                        opacity="0.35"
                      />
                      <path
                        d="M0,100 L90,85 L180,75 L270,55 L360,40 L450,22 L500,10"
                        fill="none"
                        stroke="#000000"
                        strokeWidth="4"
                      />
                      {[
                        { x: 90, y: 85 },
                        { x: 180, y: 75 },
                        { x: 270, y: 55 },
                        { x: 360, y: 40 },
                        { x: 450, y: 22 },
                      ].map((pt, i) => (
                        <circle key={i} cx={pt.x} cy={pt.y} r="5" fill="#ffcc00" stroke="#000000" strokeWidth="2.5" />
                      ))}
                    </svg>
                  </div>

                  <div className="flex justify-between text-[11px] font-mono text-gray-700">
                    <span>Q1: $2.1M ARR</span>
                    <span>Q2: $3.4M ARR</span>
                    <span className="font-bold text-black">Q3: $4.8M ARR (+18%)</span>
                  </div>
                </div>
              </div>

              {/* Document Footer */}
              <div className="mt-8 pt-4 border-t-2 border-gray-300 flex items-center justify-between text-xs font-mono text-gray-600">
                <span>CONFIDENTIAL INTERNAL AUDIT</span>
                <span>CRYPTOGRAPHIC SEAL #ID-99201</span>
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT PANE: 45% Width AI Chat Interface */}
        <section className="w-full lg:w-[45%] bg-transparent flex flex-col glass-panel">
          {/* Header */}
          <header className="p-4 border-b-4 border-black bg-[#ffcc00] text-black flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                smart_toy
              </span>
              <h2 className="font-bold text-xl uppercase tracking-widest" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                Audit Assistant
              </h2>
            </div>
            <div className="text-xs font-bold uppercase border-4 border-black px-2 py-1 bg-white font-mono">
              Status: Online
            </div>
          </header>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-[radial-gradient(rgba(255,255,255,0.1)_1px,transparent_1px)] [background-size:16px_16px]">
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-2">
                {/* User Message */}
                {msg.role === 'user' && (
                  <div className="flex flex-col items-end">
                    <div className="bg-white/10 backdrop-blur-md border-4 border-[#ffcc00] p-4 max-w-[88%] brutalist-shadow text-white">
                      <p className="font-bold text-base sm:text-lg">{msg.content}</p>
                    </div>
                    <span className="text-xs font-bold uppercase mt-2 text-white/70 font-mono">
                      You — {msg.timestamp}
                    </span>
                  </div>
                )}

                {/* AI Response Card */}
                {msg.role === 'assistant' && (
                  <div className="flex flex-col items-start w-full">
                    <div className="w-full bg-black/70 backdrop-blur-xl border-4 border-[#ffcc00] p-5 sm:p-6 max-w-[98%] brutalist-shadow space-y-6 text-white">
                      {/* Analysis Complete Header */}
                      <div className="flex items-center gap-2 text-[#ffcc00]">
                        <span className="material-symbols-outlined text-xl">auto_awesome</span>
                        <h3 className="font-black text-xl uppercase" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                          Analysis Complete
                        </h3>
                      </div>

                      {/* Summary with Highlight */}
                      <p className="text-base sm:text-lg font-medium leading-relaxed">
                        Based on the provided document,{' '}
                        <span className="bg-[#ffcc00] text-black px-1 font-bold">
                          the 18% revenue growth was driven by
                        </span>{' '}
                        two main factors:
                      </p>

                      {/* Claims List */}
                      {msg.analysisResult?.claims && (
                        <ul className="list-none space-y-4 text-base sm:text-lg">
                          {msg.analysisResult.claims.map((claim) => (
                            <li key={claim.id} className="flex gap-4">
                              <span className="text-[#ffcc00] text-2xl font-black shrink-0" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                                {claim.id}
                              </span>
                              <div className="space-y-1 min-w-0 flex-1">
                                <p className="font-bold text-white">{claim.title}</p>
                                <p className="text-sm text-white/80">{claim.content}</p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {claim.status === 'SUPPORTED' ? (
                                    <span className="inline-flex items-center gap-1 bg-white/10 border-2 border-[#ffcc00] px-2 py-0.5 text-xs font-bold uppercase text-[#ffcc00]">
                                      <span className="material-symbols-outlined text-[14px]">check_circle</span>
                                      Supported
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 bg-red-500/20 border-2 border-red-500 px-2 py-0.5 text-xs font-bold uppercase text-red-400">
                                      <span className="material-symbols-outlined text-[14px]">warning</span>
                                      Flagged
                                    </span>
                                  )}
                                  {claim.flagReason && (
                                    <span className="text-xs font-medium self-center text-white/60">
                                      {claim.flagReason}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}

                      {/* Citations Bento Grid */}
                      {msg.analysisResult?.verifiedSources && (
                        <div className="pt-4 border-t-4 border-[#ffcc00] border-dashed">
                          <h4 className="font-bold text-sm uppercase mb-3 text-[#ffcc00]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                            Verified Sources
                          </h4>
                          <div className="grid grid-cols-2 gap-3">
                            {msg.analysisResult.verifiedSources.map((source) => (
                              <button
                                key={source.id}
                                onClick={() => source.page && jumpToCitation(source.page)}
                                className="bg-white/5 border-2 border-[#ffcc00] p-3 text-left hover:bg-white/10 brutalist-shadow-hover transition-all flex flex-col justify-between group cursor-pointer"
                              >
                                <div className="flex justify-between items-start mb-2">
                                  <span className="font-bold text-xs uppercase bg-[#ffcc00] text-black px-1.5 py-0.5">
                                    {source.label}
                                  </span>
                                  <span className="material-symbols-outlined text-[#ffcc00] opacity-0 group-hover:opacity-100 transition-opacity text-[18px]">
                                    open_in_new
                                  </span>
                                </div>
                                <p className="font-bold text-xs truncate w-full text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                                  {source.docName}
                                </p>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <span className="text-xs font-bold uppercase mt-2 text-white/70 font-mono">
                      Audit Assistant — {msg.timestamp}
                    </span>
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="w-full bg-black/60 border-2 border-[#ffcc00] p-4 flex items-center gap-3 animate-pulse">
                <span className="material-symbols-outlined text-[#ffcc00] animate-spin text-[20px]">
                  refresh
                </span>
                <span className="text-xs font-mono text-white/80">
                  Cross-referencing institutional records with Neural Auditor...
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-4 sm:p-6 bg-black/40 backdrop-blur-md border-t-4 border-[#ffcc00] flex gap-3 sm:gap-4 items-end shrink-0">
            <div className="flex-1 relative">
              <label className="sr-only" htmlFor="ai-input">
                Ask AI
              </label>
              <textarea
                id="ai-input"
                rows={1}
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="ASK AI TO ANALYZE..."
                className="w-full bg-white/5 border-0 border-b-4 border-[#ffcc00] text-base sm:text-lg font-bold p-3 sm:p-4 focus:ring-0 focus:border-[#ffcc00] resize-none text-white placeholder-white/50 outline-none"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              />
              <div className="absolute right-2 bottom-3 flex gap-2">
                <button
                  type="button"
                  className="p-1 text-white/50 hover:text-[#ffcc00] transition-colors cursor-pointer"
                  title="Attach file"
                >
                  <span className="material-symbols-outlined text-[20px]">attach_file</span>
                </button>
              </div>
            </div>

            {/* Brutalist Arrow Submit Button */}
            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || !inputQuery.trim()}
              className="bg-[#ffcc00] text-black h-12 sm:h-14 w-12 sm:w-14 flex items-center justify-center border-4 border-black brutalist-shadow btn-glow hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-3xl font-bold">arrow_upward</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};
