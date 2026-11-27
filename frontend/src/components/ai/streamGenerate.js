import { API } from '@/config/constants';

// POSTs to the SSE endpoint and calls onDelta for each chunk. Resolves with the final "done" payload.
export async function streamGenerate(body, onDelta) {
  const res = await fetch(`${API}/ai/generate`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Generation failed');
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let done = null;
  for (;;) {
    const { value, done: end } = await reader.read();
    if (end) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split('\n\n');
    buf = frames.pop();
    for (const f of frames) {
      if (!f.startsWith('data: ')) continue;
      const msg = JSON.parse(f.slice(6));
      if (msg.type === 'delta') onDelta(msg.content);
      else if (msg.type === 'error') throw new Error(msg.detail);
      else if (msg.type === 'done') done = msg;
    }
  }
  if (!done) throw new Error('Generation was interrupted');
  return done;
}
