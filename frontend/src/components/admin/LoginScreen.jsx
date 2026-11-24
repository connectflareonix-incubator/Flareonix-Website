import React, { useState } from 'react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '@/config/constants';
import { adminSetToken } from './adminAuth';
import { apiError } from './apiError';
import { ForgotPassword } from './ForgotPassword';
import { AuthCard, authInput, authButton, authButtonStyle } from './AuthCard';

export const LoginScreen = ({ onSuccess }) => {
  const [email, setEmail] = useState('');
  const [pwd, setPwd] = useState('');
  const [loading, setLoading] = useState(false);
  const [forgot, setForgot] = useState(false);

  if (forgot) return <ForgotPassword onBack={() => setForgot(false)} />;

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await axios.post(`${API}/admin/login`, { email, password: pwd }, { withCredentials: true });
      adminSetToken(r.data.token);
      toast.success('Signed in');
      onSuccess();
    } catch (err) {
      toast.error(apiError(err, 'Invalid email or password'));
    }
    setLoading(false);
  };

  return (
    <AuthCard title="Flareonix Admin" subtitle="Sign in with your admin credentials">
      <form onSubmit={submit} className="space-y-4">
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
          className={authInput} required autoComplete="username" data-testid="admin-email" />
        <input type="password" value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder="Password"
          className={authInput} required autoComplete="current-password" data-testid="admin-password" />
        <button type="submit" disabled={loading} className={authButton} style={authButtonStyle} data-testid="admin-login-btn">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <button type="button" onClick={() => setForgot(true)} className="block mx-auto text-xs text-white/50 hover:text-[#FF6B00]" data-testid="admin-forgot-link">
        Forgot password?
      </button>
    </AuthCard>
  );
};

export default LoginScreen;
