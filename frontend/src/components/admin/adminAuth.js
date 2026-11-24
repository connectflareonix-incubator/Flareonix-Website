/* Admin session helper: keeps a short-lived admin token (never the password) in sessionStorage. */
const KEY = 'flareonix_admin_token';

sessionStorage.removeItem('flareonix_admin_creds');

export const adminSetToken = (token) => sessionStorage.setItem(KEY, token);

export const adminGetToken = () => sessionStorage.getItem(KEY);

export const adminClear = () => sessionStorage.removeItem(KEY);

export const adminAuthConfig = () => {
  const t = adminGetToken();
  return { withCredentials: true, headers: t ? { Authorization: `Bearer ${t}` } : {} };
};
