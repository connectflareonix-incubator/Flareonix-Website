import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '@/config/constants';
import { apiError } from '@/components/admin/apiError';
import { adminClear } from '@/components/admin/adminAuth';
import { AuthCard, authInput, authButton, authButtonStyle } from '@/components/admin/AuthCard';

export default function AdminResetPasswordPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const token = params.get('token') || '';
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (pwd !== confirm) { setError('The two passwords do not match.'); return; }
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API}/admin/reset-password`, { token, new_password: pwd });
      adminClear();
      toast.success('Password updated. Sign in with your new password.');
      nav('/admin', { replace: true });
    } catch (err) {
      setError(apiError(err, 'Could not reset the password.'));
    }
    setLoading(false);
  };

  return (
    <AuthCard title="Choose a new admin password" subtitle="At least 12 characters, with letters and numbers">
      {!token ? (
        <p className="text-red-400 text-sm text-center" data-testid="admin-reset-missing">This reset link is incomplete. Request a new one from the sign-in page.</p>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="admin-reset-form">
          <input type="password" value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder="New password" minLength={12}
            className={authInput} required autoComplete="new-password" data-testid="admin-reset-password" />
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Confirm new password" minLength={12}
            className={authInput} required autoComplete="new-password" data-testid="admin-reset-confirm" />
          {error && <p className="text-red-400 text-xs" data-testid="admin-reset-error">{error}</p>}
          <button type="submit" disabled={loading} className={authButton} style={authButtonStyle} data-testid="admin-reset-submit">
            {loading ? 'Saving…' : 'Save new password'}
          </button>
        </form>
      )}
    </AuthCard>
  );
}
