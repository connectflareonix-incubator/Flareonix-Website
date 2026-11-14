import React, { useEffect, useState } from 'react';
import { Edit2, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '../adminApi';
import { apiError } from '../apiError';
import { Card, SectionHeader, Loader, Pill } from '../ui';
import PolicyEditor from './PolicyEditor';

const Policies = () => {
  const [items, setItems] = useState(null);
  const [editing, setEditing] = useState(null);

  const load = async () => setItems(await adminApi.listPolicies());
  useEffect(() => { load(); }, []);

  const toggleNotice = async (p) => {
    try {
      await adminApi.setPolicyNotice(p.slug, !p.show_draft_notice);
      toast.success(p.show_draft_notice ? 'Draft notice removed' : 'Draft notice shown');
      load();
    } catch (err) { toast.error(apiError(err)); }
  };

  if (editing) return <PolicyEditor slug={editing} onDone={() => { setEditing(null); load(); }} />;
  if (items === null) return <Loader />;

  return (
    <div data-testid="admin-policies">
      <SectionHeader title="Policies" />
      <p className="text-xs text-white/50 mb-4">These are drafts written for review by your lawyer. Remove the draft notice only once a policy is approved.</p>
      <Card>
        <table className="w-full text-sm">
          <thead className="text-left text-white/60"><tr><th className="p-2">Policy</th><th className="p-2">Version</th><th className="p-2">Draft notice</th><th></th></tr></thead>
          <tbody>{items.map((p) => (
            <tr key={p.slug} className="border-t border-white/5" data-testid={`admin-policy-row-${p.slug}`}>
              <td className="p-2">{p.title}</td>
              <td className="p-2 text-white/70">v{p.version}</td>
              <td className="p-2">
                <button onClick={() => toggleNotice(p)} data-testid={`admin-policy-notice-${p.slug}`}>
                  <Pill color={p.show_draft_notice ? 'orange' : 'green'}>{p.show_draft_notice ? 'Shown: click to remove' : 'Removed: click to show'}</Pill>
                </button>
              </td>
              <td className="p-2 text-right whitespace-nowrap">
                <a href={`/policies/${p.slug}`} target="_blank" rel="noreferrer" title="View" className="inline-block p-1.5 hover:bg-white/10 rounded mr-1"><ExternalLink className="h-4 w-4" /></a>
                <button onClick={() => setEditing(p.slug)} title="Edit" className="p-1.5 hover:bg-white/10 rounded" data-testid={`admin-policy-edit-${p.slug}`}><Edit2 className="h-4 w-4" /></button>
              </td>
            </tr>
          ))}</tbody>
        </table>
      </Card>
    </div>
  );
};

export default Policies;
