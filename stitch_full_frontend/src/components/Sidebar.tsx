import React from 'react';
import { NavView, UserSession } from '../types';
import { BrandLogo } from './BrandLogo';

interface SidebarProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  onNewAnalysis: () => void;
  user: UserSession;
  onSignOut: () => void;
  onOpenAuth: () => void;
  documentsCount: number;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  onNewAnalysis,
  user,
  onSignOut,
  onOpenAuth,
  documentsCount,
  isOpenMobile = false,
  onCloseMobile,
}) => {
  const handleItemClick = (view: NavView) => {
    onNavigate(view);
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpenMobile && (
        <div 
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 md:hidden"
        />
      )}

      <aside 
        id="main-sidebar"
        className={`fixed md:static inset-y-0 left-0 z-50 w-[280px] bg-[#121214]/60 backdrop-blur-md border-r border-white/10 flex flex-col py-5 shrink-0 select-none text-white font-sans glass-panel transform transition-transform duration-200 ease-in-out ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="px-6 mb-6 flex items-center gap-3">
          <BrandLogo size={36} />
          <div>
            <div className="font-bold text-white text-lg tracking-tight leading-none" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              InsightDocs
            </div>
            <div className="text-[10px] uppercase font-mono tracking-widest text-[#ffcc00] mt-1 font-semibold">
              AI Audit Engine
            </div>
          </div>
        </div>

        {/* New Analysis Primary Button matching reference */}
        <div className="px-4 mb-6">
          <button
            id="btn-new-analysis"
            onClick={() => {
              onNewAnalysis();
              if (onCloseMobile) onCloseMobile();
            }}
            className="w-full flex items-center justify-center gap-2 bg-[#ffcc00] text-black text-sm py-2.5 rounded-xl transition-all duration-300 btn-glow border-beam-container hover:scale-105 transition-transform font-bold cursor-pointer shadow-lg shadow-amber-400/20"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined text-[20px]">add</span>
            <span>New Analysis</span>
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-2 space-y-1.5">
          {/* Documents Tab */}
          <button
            id="nav-item-documents"
            onClick={() => handleItemClick('documents')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-r-lg transition-all duration-300 relative overflow-hidden group cursor-pointer text-left ${
              currentView === 'documents'
                ? 'bg-amber-400/15 text-[#ffcc00] border-l-2 border-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10 rounded-lg'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <div className="absolute inset-0 bg-[#ffcc00]/5 translate-x-[-100%] group-hover:translate-x-0 transition-transform duration-300 ease-out" />
            <span 
              className="material-symbols-outlined relative z-10 text-[20px]"
              style={currentView === 'documents' ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              description
            </span>
            <span className="text-sm relative z-10 text-white">Documents</span>
            {documentsCount > 0 && (
              <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-mono font-bold bg-white/10 text-white/90">
                {documentsCount}
              </span>
            )}
          </button>

          {/* Audit & Workspace Tab */}
          <button
            id="nav-item-audit"
            onClick={() => handleItemClick('audit')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-r-lg transition-all duration-300 relative overflow-hidden group cursor-pointer text-left ${
              currentView === 'audit'
                ? 'bg-amber-400/15 text-[#ffcc00] border-l-2 border-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10 rounded-lg'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span 
              className="material-symbols-outlined relative z-10 text-[20px] group-hover:scale-110 transition-transform duration-300"
              style={currentView === 'audit' ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              fact_check
            </span>
            <span className="text-sm relative z-10">Audit & Chat</span>
          </button>

          {/* Chat History Tab */}
          <button
            id="nav-item-chat-history"
            onClick={() => handleItemClick('chat-history')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-r-lg transition-all duration-300 relative overflow-hidden group cursor-pointer text-left ${
              currentView === 'chat-history'
                ? 'bg-amber-400/15 text-[#ffcc00] border-l-2 border-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10 rounded-lg'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined relative z-10 text-[20px] group-hover:scale-110 transition-transform duration-300">
              history
            </span>
            <span className="text-sm relative z-10">Chat History</span>
          </button>

          {/* Settings Tab */}
          <button
            id="nav-item-settings"
            onClick={() => handleItemClick('settings')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-r-lg transition-all duration-300 relative overflow-hidden group cursor-pointer text-left ${
              currentView === 'settings'
                ? 'bg-amber-400/15 text-[#ffcc00] border-l-2 border-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10 rounded-lg'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined relative z-10 text-[20px] group-hover:scale-110 transition-transform duration-300">
              settings
            </span>
            <span className="text-sm relative z-10">Settings</span>
          </button>

          {/* BYOK Config Tab */}
          <button
            id="nav-item-byok"
            onClick={() => handleItemClick('byok')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-r-lg transition-all duration-300 relative overflow-hidden group cursor-pointer text-left ${
              currentView === 'byok'
                ? 'bg-amber-400/15 text-[#ffcc00] border-l-2 border-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10 rounded-lg'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined relative z-10 text-[20px] group-hover:scale-110 transition-transform duration-300">
              key
            </span>
            <span className="text-sm relative z-10">BYOK Config</span>
          </button>
        </nav>

        {/* Bottom Section: Help & User Account */}
        <div className="mt-auto px-2 space-y-1.5 pt-4 border-t border-white/10">
          <button
            id="nav-item-help"
            onClick={() => handleItemClick('help')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300 group cursor-pointer text-left ${
              currentView === 'help'
                ? 'bg-amber-400/15 text-[#ffcc00] font-bold'
                : 'text-white/70 hover:text-white hover:bg-white/10'
            }`}
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            <span className="material-symbols-outlined group-hover:scale-110 transition-transform duration-300 text-[20px]">
              help
            </span>
            <span className="text-sm">Help</span>
          </button>

          {user.isAuthenticated ? (
            <button
              id="btn-sign-out"
              onClick={onSignOut}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-white/70 hover:text-red-400 hover:bg-white/10 transition-all duration-300 rounded-lg group cursor-pointer text-left"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              <span className="material-symbols-outlined group-hover:scale-110 transition-transform duration-300 text-[20px]">
                logout
              </span>
              <span className="text-sm">Sign Out</span>
            </button>
          ) : (
            <button
              id="btn-sign-in-prompt"
              onClick={() => {
                onOpenAuth();
                if (onCloseMobile) onCloseMobile();
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-white/70 hover:text-[#ffcc00] hover:bg-white/10 transition-all duration-300 rounded-lg group cursor-pointer text-left"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              <span className="material-symbols-outlined group-hover:scale-110 transition-transform duration-300 text-[20px]">
                login
              </span>
              <span className="text-sm">Sign In</span>
            </button>
          )}
        </div>
      </aside>
    </>
  );
};
