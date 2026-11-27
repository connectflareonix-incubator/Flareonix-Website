import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'axios';
import { API } from '@/config/constants';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

const PolicyPage = () => {
  const { slug } = useParams();
  const [policy, setPolicy] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setPolicy(null);
    setError(false);
    axios.get(`${API}/policies/${encodeURIComponent(slug)}`)
      .then(r => { if (active) setPolicy(r.data); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [slug]);

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      <Navbar />
      <main className="max-w-4xl mx-auto px-5 py-16 min-h-[60vh]">
        <Link to="/" className="text-sm text-[#FF6B00]">← Back to Flareonix</Link>
        {policy ? (
          <>
            <h1 className="text-3xl md:text-4xl font-bold mt-6 mb-3">{policy.title}</h1>
            <p className="text-xs text-white/40 mb-8">Version {policy.version} · Published {policy.published_at ? new Date(policy.published_at).toLocaleDateString() : ''}</p>
            <article className="whitespace-pre-wrap leading-8 text-white/80">{policy.content}</article>
          </>
        ) : error ? (
          <div className="mt-12"><h1 className="text-2xl font-bold">Policy not available</h1><p className="text-white/60 mt-2">This policy has not been published yet. Please contact Flareonix if you need clarification.</p></div>
        ) : <p className="mt-12 text-white/60">Loading policy…</p>}
      </main>
      <Footer />
    </div>
  );
};

export default PolicyPage;
