import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft } from 'lucide-react';
import { API } from '@/config/constants';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { DraftNotice } from '@/components/policy/DraftNotice';
import { PolicyBody } from '@/components/policy/PolicyBody';

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }) : '');

export default function PolicyPage({ slug: fixedSlug }) {
  const params = useParams();
  const slug = fixedSlug || params.slug;
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setDoc(null);
    setError(false);
    axios.get(`${API}/policies/${slug}`)
      .then((r) => { setDoc(r.data); document.title = `${r.data.title} | Flareonix`; window.scrollTo(0, 0); })
      .catch(() => setError(true));
  }, [slug]);

  return (
    <main className="min-h-screen bg-[#050505]">
      <Navbar />
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-3xl mx-auto" data-testid="policy-page">
          <Link to="/policies" className="inline-flex items-center gap-2 text-sm text-white/50 hover:text-white mb-6" data-testid="policy-back-link">
            <ArrowLeft className="h-4 w-4" /> All policies
          </Link>
          {error && <p className="text-white/60" data-testid="policy-not-found">This policy could not be found.</p>}
          {!doc && !error && <p className="text-white/40" data-testid="policy-loading">Loading…</p>}
          {doc && (
            <>
              <h1 className="font-heading text-4xl sm:text-5xl font-black text-white mb-3" data-testid="policy-title">{doc.title}</h1>
              <p className="text-sm text-white/40 mb-8" data-testid="policy-meta">Version {doc.version} · Last updated {fmt(doc.updated_at)}</p>
              {doc.show_draft_notice && <DraftNotice />}
              <PolicyBody markdown={doc.body_md} />
            </>
          )}
        </div>
      </section>
      <Footer />
    </main>
  );
}
