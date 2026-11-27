import React, { useEffect, useState } from 'react';
import { adminApi } from '../adminApi';
import { Card, SectionHeader, PrimaryButton, TextInput, Textarea, Loader } from '../ui';
import { toast } from 'sonner';

const GROUPS = {
  'Contact & Social': ['contact_email', 'contact_phone', 'contact_whatsapp', 'contact_address', 'social_instagram', 'social_linkedin', 'whatsapp_community', 'calendly_link'],
  'Business & Tax': ['gstin'],
  'Content': ['tagline', 'mission', 'stat_founders', 'stat_businesses', 'stat_projects'],
};

const Settings = () => {
  const [vals, setVals] = useState(null);
  const [draft, setDraft] = useState({});

  const load = async () => {
    const v = await adminApi.getSettings();
    setVals(v);
    setDraft(v);
  };
  useEffect(() => { load().catch(() => toast.error('Could not load settings')); }, []);

  const save = async (key) => {
    const value = key === 'gstin' ? String(draft[key] || '').trim().toUpperCase() : draft[key];
    if (key === 'gstin' && value && !/^[0-9A-Z]{15}$/.test(value)) {
      toast.error('GSTIN must contain exactly 15 letters/numbers.');
      return;
    }
    try {
      await adminApi.setSetting(key, value);
      toast.success('Saved');
      await load();
    } catch {
      toast.error('Failed to save setting');
    }
  };

  if (vals === null) return <Loader />;

  const renderField = (key) => {
    const v = draft[key];
    const isLong = key === 'mission';
    return (
      <div key={key} className="flex flex-col md:flex-row md:items-start md:gap-4">
        <label className="text-xs text-white/60 md:w-48 md:pt-2">{key === 'gstin' ? 'GSTIN No. (optional)' : key.replace(/_/g, ' ')}</label>
        <div className="flex-1 flex gap-2">
          {isLong
            ? <Textarea rows={3} value={v || ''} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
            : <TextInput value={v ?? ''} onChange={(e) => setDraft({ ...draft, [key]: key === 'gstin' ? e.target.value.toUpperCase().slice(0, 15) : e.target.value })} />}
          <PrimaryButton onClick={() => save(key)}>Save</PrimaryButton>
        </div>
      </div>
    );
  };

  return (
    <div data-testid="admin-settings">
      <SectionHeader title="Settings" subtitle="Editable globals used across the public site" />
      {Object.entries(GROUPS).map(([title, keys]) => (
        <Card key={title} className="mb-4 space-y-3">
          <h3 className="font-semibold mb-2">{title}</h3>
          {title === 'Business & Tax' && (
            <p className="text-xs text-white/50">Leave GSTIN blank until it is officially allotted. Do not enter a provisional or invented number.</p>
          )}
          {keys.map(renderField)}
        </Card>
      ))}
    </div>
  );
};

export default Settings;
