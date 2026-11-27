import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API } from '@/config/constants';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include'
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip the /me check.
    // AuthCallback will exchange the session_id and establish the session first.
 if (window.location.pathname === '/auth/callback') {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = async () => {
    try {
      const encodeBase64Url = (bytes) => {
        let binary = '';
        bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
      };
      const state = encodeBase64Url(crypto.getRandomValues(new Uint8Array(32)));
      const verifier = encodeBase64Url(crypto.getRandomValues(new Uint8Array(32)));
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
      const challenge = encodeBase64Url(new Uint8Array(digest));
      sessionStorage.setItem('flareonix_oauth_state', state);
      sessionStorage.setItem('flareonix_oauth_verifier', verifier);
      const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
      const redirectUri = encodeURIComponent(window.location.origin + '/auth/callback');
      const scope = encodeURIComponent('openid email profile');
      const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: window.location.origin + '/auth/callback',
        response_type: 'code',
        scope: 'openid email profile',
        access_type: 'online',
        state,
        code_challenge: challenge,
        code_challenge_method: 'S256',
      });
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
    } catch (error) {
      console.error('Could not securely start Google sign-in:', error);
      sessionStorage.removeItem('flareonix_oauth_state');
      sessionStorage.removeItem('flareonix_oauth_verifier');
      window.location.href = '/login?error=oauth_unavailable';
    }
  };
  
  const logout = async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Logout failed:', error);
    }
    setUser(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
