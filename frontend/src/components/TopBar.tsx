import React from 'react';
import { NavView, ByokConfig, UserSession } from '../types';
import { BrandLogo } from './BrandLogo';

interface TopBarProps {
  currentView: NavView;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  byokConfig: ByokConfig;
  user: UserSession;
  onOpenAuth: () => void;
  onToggleMobileMenu?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentView,
  searchQuery,
  onSearchChange,
  byokConfig,
  user,
  onOpenAuth,
  onToggleMobileMenu,
}) => {
  return (
    <header 
      id="app-topbar"
      className="fixed top-0 right-0 w-full md:w-[calc(100%-280px)] z-30 bg-[#121214]/40 backdrop-blur-xl border-b border-white/10 flex justify-between items-center h-16 px-6 glass-panel select-none"
    >
      <div className="flex items-center gap-4 flex-1">
        {/* Mobile menu hamburger */}
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-2 text-white/70 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
            title="Toggle Navigation Menu"
          >
            <span className="material-symbols-outlined text-[22px]">menu</span>
          </button>
        )}

        {/* Global Search Input Bar matching exact reference */}
        <div className="relative w-full max-w-sm sm:max-w-md focus-within:ring-1 focus-within:ring-[#ffcc00] rounded-lg transition-all duration-300 group">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-white/70 group-focus-within:text-[#ffcc00] transition-colors text-[18px]">
            search
          </span>
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documents, entities, or insights..."
            className="w-full bg-white/5 border border-white/10 text-white placeholder-white/50 pl-10 pr-4 py-2 rounded-lg focus:border-[#ffcc00] focus:bg-white/10 focus:ring-0 text-sm transition-all duration-300 font-sans outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs font-mono text-white/50 hover:text-[#ffcc00] cursor-pointer"
            >
              ESC
            </button>
          )}
        </div>
      </div>

      {/* Right Brand Badge matching reference image */}
      <div className="flex items-center gap-4">
        {/* BYOK / Model Status Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-white/80">
          <span className={`w-2 h-2 rounded-full ${byokConfig.enabled ? 'bg-green-400 shadow-[0_0_6px_#4ade80]' : 'bg-[#ffcc00]'}`} />
          <span className="font-mono text-[11px]">
            {byokConfig.enabled ? byokConfig.selectedModel : 'Gemini 3.7 Flash'}
          </span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold ${
            byokConfig.enabled ? 'bg-green-500/20 text-green-300' : 'bg-amber-400/20 text-[#ffcc00]'
          }`}>
            {byokConfig.enabled ? 'BYOK' : 'PRO'}
          </span>
        </div>

        {/* InsightDocs Brand Asset badge with custom 3D Hexagon ribbon logo */}
        <div className="flex items-center gap-2.5 mr-2">
          <BrandLogo size={32} />
          <span className="font-bold text-white text-base tracking-tight hidden sm:inline" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            InsightDocs
          </span>
        </div>

        {/* User / Sign In Button */}
        {!user.isAuthenticated ? (
          <button
            id="btn-topbar-login"
            onClick={onOpenAuth}
            className="text-xs font-bold text-black bg-[#ffcc00] hover:bg-[#e6b800] px-3.5 py-1.5 rounded-lg transition-all duration-300 cursor-pointer btn-glow font-headline"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            Sign In
          </button>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer text-xs"
          >
            <div className="w-6 h-6 rounded-full bg-[#ffcc00] text-black font-bold flex items-center justify-center text-[10px] font-mono">
              {user.name.slice(0, 2).toUpperCase()}
            </div>
            <span className="font-semibold text-white hidden md:inline">{user.name}</span>
          </button>
        )}
      </div>
    </header>
  );
};
