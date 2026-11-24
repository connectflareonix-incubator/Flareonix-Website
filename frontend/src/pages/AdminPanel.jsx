import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '@/config/constants';
import { adminAuthConfig } from '@/components/admin/adminAuth';
import { LoginScreen } from '@/components/admin/LoginScreen';
import AdminLayout from '@/components/admin/AdminLayout';
import Dashboard from '@/components/admin/sections/Dashboard';
import Blog from '@/components/admin/sections/Blog';
import Team from '@/components/admin/sections/Team';
import Projects from '@/components/admin/sections/Projects';
import Collaborations from '@/components/admin/sections/Collaborations';
import Inbox from '@/components/admin/sections/Inbox';
import Feedback from '@/components/admin/sections/Feedback';
import Users from '@/components/admin/sections/Users';
import Announcements from '@/components/admin/sections/Announcements';
import Settings from '@/components/admin/sections/Settings';

const AdminPanel = () => {
  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    axios.get(`${API}/admin/verify`, adminAuthConfig())
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return <div className="min-h-screen bg-[#0D0D0D] flex items-center justify-center text-white/70">Checking admin session…</div>;
  }

  if (!authed) return <LoginScreen onSuccess={() => setAuthed(true)} />;

  return (
    <AdminLayout>
      <Routes>
        <Route path="/" element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="blog" element={<Blog />} />
        <Route path="team" element={<Team />} />
        <Route path="projects" element={<Projects />} />
        <Route path="collaborations" element={<Collaborations />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="feedback" element={<Feedback />} />
        <Route path="users" element={<Users />} />
        <Route path="announcements" element={<Announcements />} />
        <Route path="settings" element={<Settings />} />
      </Routes>
    </AdminLayout>
  );
};

export default AdminPanel;
