import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { API } from '@/config/constants';

export const ModelPicker = ({ value, onChange }) => {
  const [models, setModels] = useState([]);

  useEffect(() => {
    axios.get(`${API}/ai/models`).then((r) => {
      setModels(r.data || []);
      const def = (r.data || []).find((m) => m.default);
      if (!value && def) onChange(def.id);
    }).catch(() => {});
  }, []); // eslint-disable-line

  return (
    <div data-testid="ai-model-picker">
      <p className="text-white text-sm font-medium mb-2">Choose your AI model</p>
      <div className="grid sm:grid-cols-3 gap-2">
        {models.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => onChange(m.id)}
            data-testid={`ai-model-${m.id}`}
            aria-pressed={value === m.id}
            className={`text-left p-3 rounded-xl border transition-colors ${value === m.id ? 'border-primary bg-primary/10' : 'border-white/10 bg-black/40 hover:border-white/30'}`}
          >
            <span className="block text-sm font-semibold text-white">{m.label}</span>
            <span className="block text-xs text-muted-foreground mt-0.5">{m.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ModelPicker;
