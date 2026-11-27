/**
 * Return a safe, user-readable message from an API error.
 * FastAPI validation and HTTP errors commonly expose a string in
 * response.data.detail; other endpoints may use message or error.
 */
export const apiError = (error, fallback = 'Something went wrong. Please try again.') => {
  const data = error?.response?.data;
  const candidates = [data?.detail, data?.message, data?.error, error?.message];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim();
    }
  }

  return fallback;
};

export default apiError;
