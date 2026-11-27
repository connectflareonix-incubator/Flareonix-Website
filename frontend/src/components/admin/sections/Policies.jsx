import React, { useEffect, useState } from 'react';
import { adminApi } from '../adminApi';
import { Card, SectionHeader, PrimaryButton, GhostButton, TextInput, Textarea, Loader, Pill } from '../ui';
import { toast } from 'sonner';

const Policies = () => {
  const [items, setItems] = useState(null);
  const [selected, setSelected] = useState(null);
  const [draft, setDraft] = useState(null);
  const [versions, setVersions] = useState([]);
  const [publishing, setPublishing] = useState(false);

  const load = async () => setItems(await adminApi.listPolicies());
  useEffect(() => { load().catch(() => toast.error('Could not load policies')); }, []);

  const open = async (slug) => {
    try {
      const [policy, history] = await Promise.all([
        adminApi.getPolicy(slug), adminApi.policyVersions(slug),
      ]);
      setSelected(slug);
      setDraft(policy);
      setVersions(history);
    } catch { toast.error('Could not open policy'); }
  };

  const save = async (publish) => {
    if (!draft || !selected) return;
    if (publish && !window.confirm('Publish this legal policy publicly? Please verify the text before continuing.')) return;
    setPublishing(true);
    try {
      await adminApi.updatePolicy(selected, {
        title: draft.title,
        content: draft.content,
        expected_version: draft.version || 0,
        publish,
      });
      toast.success(publish ? 'New policy version published' : 'Draft version saved');
      await open(selected);
      await load();
    } catch (e) {
      toast.error(e?.response?.status === 409 ? 'This policy changed elsewhere. Reload it before saving.' : 'Could not save policy');
    } finally { setPublishing(false); }
  };

  const setNotice = async (show) => {
    try {
      await adminApi.setPolicyNotice(selected, show);
      await open(selected);
      toast.success('Draft notice updated');
    } catch { toast.error('Could not update notice'); }
  };

  if (items === null) return <Loader />;

  if (selected && draft) return (
    <div data-testid="admin-policies-editor">
      <SectionHeader title={draft.title} subtitle={`Version ${draft.version || 0} · ${draft.published ? 'Published' : 'Not published'}`}
        actions={[<GhostButton key="back" onClick={() => { setSelected(null); setDraft(null); }}>Back to policies</GhostButton>]} />
      <Card className="space-y-3 mb-4">
        <p className="text-xs text-amber-300">Legal text is not ordinary website content. Save drafts separately and publish only after review. Published versions remain in history.</p>
        <div><label className="text-xs text-white/60">Policy title</label><TextInput value={draft.title || ''} onChange={e => setDraft({ ...draft, title: e.target.value })} /></div>
        <div><label className="text-xs text-white/60">Policy content (plain text / Markdown)</label><Textarea rows={18} value={draft.content || ''} onChange={e => setDraft({ ...draft, content: e.target.value })} /></div>
        <div className="flex flex-wrap gap-2">
          <PrimaryButton disabled={publishing} onClick={() => save(false)}>Save draft version</PrimaryButton>
          <PrimaryButton disabled={publishing || !draft.content?.trim()} onClick={() => save(true)}>Publish new version</PrimaryButton>
        </div>
        {draft.published && <label className="flex items-center gap-2 text-sm text-white/70"><input type="checkbox" checked={!!draft.show_draft_notice} onChange={e => setNotice(e.target.checked)} /> Show draft / review notice where applicable</label>}
      </Card>
      <Card>
        <h3 className="font-semibold mb-3">Version history</h3>
        {versions.length ? versions.map(v => (
          <div key={v.id} className="border-t border-white/10 py-3 text-sm flex justify-between gap-3">
            <div><strong>Version {v.version}</strong><p className="text-xs text-white/50">{v.saved_at} · {v.saved_by}</p></div>
            <Pill color={v.published ? 'green' : 'gray'}>{v.published ? 'Published snapshot' : 'Draft snapshot'}</Pill>
          </div>
        )) : <p className="text-sm text-white/50">No saved versions yet.</p>}
      </Card>
    </div>
  );

  return (
    <div data-testid="admin-policies">
      <SectionHeader title="Legal & Policies" subtitle="Restricted legal documents with version history and explicit publishing." />
      <Card className="mb-4"><p className="text-sm text-white/70">Do not claim Flareonix is already a registered proprietorship. Keep legal identity and GSTIN details blank until they are formally confirmed. These are document-management controls, not a substitute for legal review.</p></Card>
      <div className="grid gap-3">
        {items.map(item => (
          <Card key={item.slug}>
            <div className="flex flex-wrap justify-between items-center gap-3">
              <div><h3 className="font-semibold">{item.title}</h3><p className="text-xs text-white/50">Version {item.version || 0}</p></div>
              <div className="flex items-center gap-3"><Pill color={item.published ? 'green' : 'gray'}>{item.published ? 'Published' : 'Draft / not published'}</Pill><PrimaryButton onClick={() => open(item.slug)}>Manage</PrimaryButton></div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Policies;
