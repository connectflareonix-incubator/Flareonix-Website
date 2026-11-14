import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { adminApi } from '../adminApi';
import { apiError } from '../apiError';
import { Card, SectionHeader, PrimaryButton, GhostButton, TextInput, Textarea, Loader } from '../ui';
import PolicyVersions from './PolicyVersions';

const PolicyEditor = ({ slug, onDone }) => {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  useEffect(() => { adminApi.getPolicy(slug).then((d) => setForm({ ...d, change_note: '' })); }, [slug]);

  const save = async () => {
    setSaving(true);
    try {
      const { title, summary, body_md, show_draft_notice, change_note } = form;
      await adminApi.updatePolicy(slug, { title, summary, body_md, show_draft_notice, change_note });
      toast.success('Saved as a new version');
      onDone();
    } catch (err) { toast.error(apiError(err, 'Failed to save')); }
    setSaving(false);
  };

  if (!form) return <Loader />;
  return (
    <div data-testid="admin-policy-editor">
      <SectionHeader title={`Edit: ${form.title} (v${form.version})`} actions={[<GhostButton key="b" onClick={onDone}>Back</GhostButton>]} />
      <Card className="space-y-3">
        <div><label className="text-xs text-white/60">Title</label><TextInput value={form.title} onChange={set('title')} data-testid="policy-title-input" /></div>
        <div><label className="text-xs text-white/60">Short summary</label><TextInput value={form.summary} onChange={set('summary')} data-testid="policy-summary-input" /></div>
        <div>
          <label className="text-xs text-white/60">Policy text (Markdown: ## heading, **bold**, - list, [link](https://…))</label>
          <Textarea rows={22} value={form.body_md} onChange={set('body_md')} className="font-mono text-xs" data-testid="policy-body-input" />
        </div>
        <div><label className="text-xs text-white/60">What changed (for the version history)</label><TextInput value={form.change_note} onChange={set('change_note')} placeholder="e.g. Lawyer edits to section 9" data-testid="policy-change-note" /></div>
        <label className="flex items-center gap-2 text-sm text-white/80" data-testid="policy-notice-checkbox">
          <input type="checkbox" checked={form.show_draft_notice} onChange={set('show_draft_notice')} /> Show the "Draft, under legal review" notice
        </label>
        <PrimaryButton onClick={save} disabled={saving} data-testid="policy-save-btn">{saving ? 'Saving…' : 'Save new version'}</PrimaryButton>
      </Card>
      <PolicyVersions slug={slug} />
    </div>
  );
};

export default PolicyEditor;
