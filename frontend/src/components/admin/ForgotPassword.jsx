import React, { useState } from 'react';
import axios from 'axios';
import { MailCheck } from 'lucide-react';
import { API } from '@/config/constants';
import { apiError } from './apiError';
import { AuthCard, authButton, authButtonStyle } from './AuthCard';

export const ForgotPassword = ({ onBack }) => {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(null);
  const [error, setError] = useState('');

  const send = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await axios.post(`${API}/admin/forgot-password`, {});
      setSent(r.data);
    } catch (err) {
      setError(apiError(err, 'Could not send the reset link. Please try again.'));
    }
    setLoading(false);
  };

  return (
    <AuthCard title="Reset admin password" subtitle="A one-time link goes to the recovery email on file">
      {sent ? (
        <div className="text-center space-y-2" data-testid="admin-forgot-sent">
          <MailCheck className="h-8 w-8 text-[#FF6B00] mx-auto" />
          <p className="text-white text-sm">Reset link sent to <strong>{sent.sent_to}</strong>.</p>
          <p className="text-white/50 text-xs">It works once and expires in {sent.expires_minutes} minutes.</p>
        </div>
      ) : (
        <button type="button" onClick={send} disabled={loading} className={authButton} style={authButtonStyle} data-testid="admin-forgot-send">
          {loading ? 'Sending…' : 'Email me a reset link'}
        </button>
      )}
      {error && <p className="text-red-400 text-xs text-center" data-testid="admin-forgot-error">{error}</p>}
      <button type="button" onClick={onBack} className="block mx-auto text-xs text-white/50 hover:text-white" data-testid="admin-forgot-back">
        Back to sign in
      </button>
    </AuthCard>
  );
};

export default ForgotPassword;
