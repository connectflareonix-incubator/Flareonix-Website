/* Admin authentication uses the HttpOnly session cookie set by the backend. */
export const adminAuthConfig = () => ({ withCredentials: true });
