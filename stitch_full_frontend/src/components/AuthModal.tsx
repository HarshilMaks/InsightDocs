import React, { useState } from 'react';
import { UserSession } from '../types';
import { BrandLogo } from './BrandLogo';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (user: UserSession) => void;
  title?: string;
  subtitle?: string;
  isRestrictedGate?: boolean;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onLoginSuccess,
  title,
  subtitle,
  isRestrictedGate = false,
}) => {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const userEmail = email.trim() || 'auditor@insightdocs.ai';
    const userName = name.trim() || userEmail.split('@')[0];

    onLoginSuccess({
      isAuthenticated: true,
      email: userEmail,
      name: userName.charAt(0).toUpperCase() + userName.slice(1),
      role: 'Lead Financial Auditor',
      avatar: '',
    });
    onClose();
  };

  const handleDemoLogin = () => {
    onLoginSuccess({
      isAuthenticated: true,
      email: 'lead.auditor@insightdocs.ai',
      name: 'Alex Vance',
      role: 'Lead Financial Auditor',
      avatar: '',
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Main Content Container matching Login / Register Refined v2 */}
      <main className="w-full max-w-md flex flex-col items-center z-10">
        {/* Branding Header */}
        <div className="flex flex-col items-center mb-6 gap-3 text-center">
          <div className="p-2 border-4 border-[#ffcc00] brutal-shadow bg-zinc-900">
            <BrandLogo size={56} />
          </div>
          <h1 className="font-black text-3xl sm:text-4xl uppercase tracking-tighter text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            InsightDocs
          </h1>
          <p className="font-bold text-sm text-[#ffcc00] uppercase tracking-widest bg-zinc-900 px-3 py-1 brutal-shadow border-2 border-[#ffcc00]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            AI Auditor
          </p>
        </div>

        {/* Auth Card */}
        <div 
          id="auth-modal-dialog"
          className="w-full bg-zinc-900 border-4 border-[#ffcc00] brutal-shadow p-6 sm:p-8 flex flex-col gap-6 relative overflow-hidden text-white"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 text-white/60 hover:text-white p-1 hover:bg-white/10 transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>

          {/* Subtitle / Gate Notice if applicable */}
          {subtitle && (
            <p className="text-xs text-white/80 font-medium text-center">
              {subtitle}
            </p>
          )}

          {/* Tabs */}
          <div className="flex border-b-4 border-[#ffcc00]">
            <button
              type="button"
              onClick={() => setActiveTab('login')}
              className={`flex-1 py-3 font-bold uppercase text-sm tracking-wider transition-colors border-r-4 border-[#ffcc00] border-t-4 border-l-4 cursor-pointer ${
                activeTab === 'login'
                  ? 'bg-[#ffcc00] text-black'
                  : 'text-white hover:bg-zinc-800'
              }`}
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('register')}
              className={`flex-1 py-3 font-bold uppercase text-sm tracking-wider transition-colors border-t-4 border-r-4 border-[#ffcc00] cursor-pointer ${
                activeTab === 'register'
                  ? 'bg-[#ffcc00] text-black'
                  : 'text-white hover:bg-zinc-800'
              }`}
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {activeTab === 'register' && (
              <div className="flex flex-col gap-1.5">
                <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  Full Name
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3 text-white/70 text-[18px]">
                    person
                  </span>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="ALEX VANCE"
                    className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white pl-10 pr-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 transition-colors text-sm"
                  />
                </div>
              </div>
            )}

            {/* Email Field */}
            <div className="flex flex-col gap-1.5">
              <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                Email Address
              </label>
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-white/70 text-[18px]">
                  mail
                </span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ENTER EMAIL"
                  className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white pl-10 pr-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 transition-colors text-sm"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="font-bold uppercase text-xs tracking-wide text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  Password
                </label>
              </div>
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-white/70 text-[18px]">
                  lock
                </span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="ENTER PASSWORD"
                  className="w-full bg-zinc-950 border-4 border-[#ffcc00] text-white pl-10 pr-4 py-2.5 focus:ring-0 focus:border-[#ffcc00] font-medium placeholder-zinc-500 transition-colors text-sm"
                />
              </div>
            </div>

            {/* Secondary Action */}
            <div className="flex justify-between items-center text-xs">
              <button
                type="button"
                onClick={handleDemoLogin}
                className="text-[#ffcc00] hover:underline font-mono cursor-pointer"
              >
                [Instant Demo Login]
              </button>
              <a 
                href="#forgot" 
                onClick={(e) => e.preventDefault()}
                className="font-bold uppercase text-[#ffcc00] hover:text-white transition-colors underline decoration-2 underline-offset-4"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              >
                Forgot Password?
              </a>
            </div>

            {/* Primary CTA */}
            <button 
              type="submit" 
              className="border-beam-container relative mt-2 group cursor-pointer"
            >
              <div 
                className="w-full bg-[#ffcc00] text-black border-4 border-black py-3.5 px-6 font-black text-lg uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-[#e6b800] transition-all brutal-shadow"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}
              >
                <span>{activeTab === 'login' ? 'Sign In' : 'Create Account'}</span>
                <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                  arrow_forward
                </span>
              </div>
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};
