import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, ArrowLeft } from 'lucide-react';

export const authInput = 'w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#FF6B00] outline-none';
export const authButton = 'w-full py-2.5 rounded-lg text-sm font-semibold text-white disabled:opacity-60';
export const authButtonStyle = { background: 'linear-gradient(135deg, #FF6B00, #CC2200)' };

export const AuthCard = ({ title, subtitle, children }) => {
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-[#0D0D0D] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Lock className="h-10 w-10 text-[#FF6B00] mx-auto mb-3" />
          <h1 className="font-heading text-2xl font-bold text-white">{title}</h1>
          <p className="text-white/50 mt-1 text-sm">{subtitle}</p>
        </div>
        <div className="p-6 bg-[#161616] border border-white/10 rounded-xl space-y-4">{children}</div>
        <button onClick={() => nav('/')} className="flex items-center gap-2 text-white/50 mx-auto mt-4 text-sm" data-testid="admin-back-to-site">
          <ArrowLeft className="h-4 w-4" />Back to site
        </button>
      </div>
    </div>
  );
};
