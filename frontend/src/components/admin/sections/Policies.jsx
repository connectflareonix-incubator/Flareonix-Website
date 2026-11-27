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
  const [reauthOpen, setReauthOpen] = useState(false);
  const [reauthPassword, setReauthPassword] = useState("");

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

  const save = async (publish, password = "") => {
    if (!draft || !selected) return;
    setPublishing(true);
    let updateCompleted = false;
    try {
      if (publish) await adminApi.reauthenticate(password);
      await adminApi.updatePolicy(selected, {
        title: draft.title,
        content: draft.content,
        expected_version: draft.version || 0,
        publish,
      });
      updateCompleted = true;
      toast.success(publish ? 'New policy version published' : 'Draft version saved');
      await open(selected);
      await load();
    } catch (e) {
      const status = e?.response?.status;
      toast.error(
        status === 401 ? 'Password incorrect or admin session expired. Please try again.' :
        status === 403 ? 'Password confirmation expired. Please confirm again.' :
        status === 429 ? 'Too many attempts. Wait before trying again.' :
        status === 409 ? 'This policy changed elsewhere. Reload it before saving.' :
        'Could not save policy'
      );
    } finally {
      setPublishing(false);
      if (publish) {
        setReauthPassword("");
        if (updateCompleted) setReauthOpen(false);
      }
    }
  };

  const confirmPublish = () => {
    if (!reauthPassword) { toast.error("Enter your admin password to publish"); return; }
    save(true, reauthPassword);
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
          <PrimaryButton disabled={publishing || !draft.content?.trim()} onClick={() => { setReauthPassword(""); setReauthOpen(true); }}>Publish new version</PrimaryButton>
        </div>
        {draft.published && <label className="flex items-center gap-2 text-sm text-white/70"><input type="checkbox" checked={!!draft.show_draft_notice} onChange={e => setNotice(e.target.checked)} /> Show draft / review notice where applicable</label>}
      </Card>
        {reauthOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal="true" aria-labelledby="policy-reauth-title">
          <div className="w-full max-w-md rounded-xl border border-white/15 bg-[#171717] p-5 shadow-2xl space-y-4">
            <div>
              <h3 id="policy-reauth-title" className="text-lg font-semibold">Confirm your identity</h3>
              <p className="mt-1 text-sm text-white/60">Enter your current admin password to publish this legal policy. Confirmation expires after five minutes.</p>
            </div>
            <label className="block text-sm text-white/70" htmlFor="policy-reauth-password">Admin password</label>
            <input id="policy-reauth-password" type="password" autoComplete="current-password" value={reauthPassword}
              onChange={e => setReauthPassword(e.target.value)} disabled={publishing}
              onKeyDown={e => { if (e.key === "Enter" && !publishing) confirmPublish(); }}
              className="w-full rounded-lg border border-white/20 bg-black/30 px-3 py-2 text-white outline-none focus:border-orange-400" />
            <div className="flex justify-end gap-2">
              <GhostButton disabled={publishing} onClick={() => { setReauthPassword(""); setReauthOpen(false); }}>Cancel</GhostButton>
              <PrimaryButton disabled={publishing || !reauthPassword} onClick={confirmPublish}>Confirm & publish</PrimaryButton>
            </div>
          </div>
        </div>}
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
