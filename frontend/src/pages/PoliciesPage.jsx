import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { ScrollText, ArrowRight } from 'lucide-react';
import { API } from '@/config/constants';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

const PolicyCard = ({ p }) => (
  <Link to={`/policies/${p.slug}`} className="group block p-6 rounded-2xl bg-[#0f0f0f] border border-white/10 hover:border-primary/40 transition-colors" data-testid={`policy-card-${p.slug}`}>
    <div className="flex items-center justify-between gap-3">
      <h2 className="font-heading text-lg font-bold text-white group-hover:text-primary transition-colors">{p.title}</h2>
      <ArrowRight className="h-4 w-4 text-primary group-hover:translate-x-1 transition-transform" />
    </div>
    <p className="text-sm text-white/60 mt-2">{p.summary}</p>
    <p className="text-xs text-white/30 mt-3">Version {p.version}{p.show_draft_notice ? ' · Draft' : ''}</p>
  </Link>
);

export default function PoliciesPage() {
  const [items, setItems] = useState(null);

  useEffect(() => {
    document.title = 'Policies | Flareonix';
    axios.get(`${API}/policies`).then((r) => setItems(r.data || [])).catch(() => setItems([]));
  }, []);

  return (
    <main className="min-h-screen bg-[#050505]">
      <Navbar />
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto" data-testid="policies-page">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border border-primary/30 text-primary mb-4">
            <ScrollText className="h-3.5 w-3.5" /> Legal
          </span>
          <h1 className="font-heading text-4xl sm:text-5xl font-black text-white mb-3">Policies &amp; terms</h1>
          <p className="text-white/60 mb-10 max-w-2xl">How Flareonix handles your data, events, passes, refunds, media and the Pitch Arena.</p>
          {items === null ? <p className="text-white/40">Loading…</p> : (
            <div className="grid md:grid-cols-2 gap-4">{items.map((p) => <PolicyCard key={p.slug} p={p} />)}</div>
          )}
        </div>
      </section>
      <Footer />
    </main>
  );
}
