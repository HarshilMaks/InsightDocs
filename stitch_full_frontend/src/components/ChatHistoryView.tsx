import React from 'react';
import { MessageSquare, Clock, ArrowUpRight, CheckCircle2, AlertTriangle, FileText, Trash2, Search } from 'lucide-react';
import { AuditSession } from '../types';

interface ChatHistoryViewProps {
  sessions: AuditSession[];
  onOpenSession: (session: AuditSession) => void;
  onDeleteSession: (id: string) => void;
  onNewAnalysis: () => void;
}

export const ChatHistoryView: React.FC<ChatHistoryViewProps> = ({
  sessions,
  onOpenSession,
  onDeleteSession,
  onNewAnalysis,
}) => {
  return (
    <div id="chat-history-view" className="flex-1 overflow-y-auto p-8 max-w-6xl mx-auto w-full font-sans text-zinc-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight uppercase">
            AUDIT SESSIONS & CHAT HISTORY
          </h1>
          <p className="text-zinc-400 text-sm mt-1.5 font-normal">
            Review past document investigations, extracted claims, and verified citations.
          </p>
        </div>

        <button
          onClick={onNewAnalysis}
          className="px-5 py-2.5 bg-[#F59E0B] hover:bg-[#d97706] text-black font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-md shadow-amber-500/10 active:scale-95 transition-all cursor-pointer shrink-0"
        >
          Start New Audit
        </button>
      </div>

      {/* Sessions List */}
      <div className="space-y-4">
        {sessions.length === 0 ? (
          <div className="p-12 text-center text-zinc-500 bg-[#14171c] border border-zinc-800 rounded-2xl">
            <MessageSquare className="w-10 h-10 mx-auto mb-3 text-zinc-600" />
            <p className="text-sm font-semibold text-zinc-300">No previous audit sessions recorded.</p>
            <p className="text-xs text-zinc-500 mt-1">Select any document from your library to start an interactive analysis.</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onOpenSession(session)}
              className="p-5 bg-[#14171c] border border-[#262c37] hover:border-amber-400/50 rounded-2xl shadow-lg transition-all cursor-pointer group flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-[#1b2029] border border-[#2b3341] group-hover:border-amber-400/50 flex items-center justify-center text-amber-400 shrink-0 transition-colors">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-bold text-white group-hover:text-amber-400 transition-colors">
                      {session.title}
                    </h3>
                    <span className="text-[11px] font-mono text-zinc-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {session.date}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-zinc-400 mb-2">
                    <FileText className="w-3.5 h-3.5 text-zinc-500" />
                    <span className="font-mono text-zinc-300">{session.documentName}</span>
                  </div>
                  <p className="text-xs text-zinc-400 line-clamp-2 max-w-2xl">
                    {session.summary}
                  </p>
                </div>
              </div>

              {/* Status & Stats */}
              <div className="flex items-center gap-3 self-end sm:self-center shrink-0">
                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {session.verifiedCount} Verified
                  </span>
                  {session.flaggedCount > 0 && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {session.flaggedCount} Flagged
                    </span>
                  )}
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenSession(session);
                  }}
                  className="p-2 text-zinc-400 hover:text-amber-400 hover:bg-[#20252e] rounded-xl transition-colors"
                  title="Resume Session"
                >
                  <ArrowUpRight className="w-5 h-5" />
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="p-2 text-zinc-500 hover:text-red-400 hover:bg-[#20252e] rounded-xl transition-colors"
                  title="Delete Session"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
