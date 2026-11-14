import React, { useEffect, useState } from 'react';
import { adminApi } from '../adminApi';
import { Card } from '../ui';

const PolicyVersions = ({ slug }) => {
  const [items, setItems] = useState([]);
  useEffect(() => { adminApi.policyVersions(slug).then(setItems).catch(() => setItems([])); }, [slug]);
  if (items.length === 0) return null;
  return (
    <Card className="mt-4" data-testid="policy-versions">
      <p className="text-sm font-semibold text-white mb-2">Earlier versions</p>
      <ul className="space-y-1 text-xs text-white/60">
        {items.map((v) => (
          <li key={`${v.version}-${v.archived_at}`}>
            v{v.version} · {new Date(v.updated_at).toLocaleString()} · {v.change_note || 'No note'}
          </li>
        ))}
      </ul>
    </Card>
  );
};

export default PolicyVersions;
