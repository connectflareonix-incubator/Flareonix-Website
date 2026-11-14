// Turns FastAPI error payloads (string or 422 list) into a readable message.
export const apiError = (err, fallback = 'Something went wrong. Please try again.') => {
  const d = err?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => e?.msg).filter(Boolean).join(' ') || fallback;
  return fallback;
};
