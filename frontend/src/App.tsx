import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import { api, session } from './api/client';
import type { Me, Notification } from './api/types';
import { ErrorNote } from './components/basics';
import { useResource } from './hooks';
import { LiveProvider, useLive } from './live/LiveProvider';
import { AdminPage } from './pages/AdminPage';
import { CommunitiesPage } from './pages/CommunitiesPage';
import { CommunityPage } from './pages/CommunityPage';
import { DraftPage } from './pages/DraftPage';
import { DraftsPage } from './pages/DraftsPage';
import { FeedPage } from './pages/FeedPage';
import { MessagesPage } from './pages/MessagesPage';
import { ModerationPage } from './pages/ModerationPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { PeoplePage } from './pages/PeoplePage';
import { PostPage } from './pages/PostPage';
import { ProfilePage } from './pages/ProfilePage';
import { SettingsPage } from './pages/SettingsPage';
import { SignInPage } from './pages/SignInPage';
import { SessionContext, useSession } from './session';

export function App() {
  const [me, setMe] = useState<Me>();
  const [loading, setLoading] = useState(session.token !== null);
  const leave = useCallback(() => {
    session.end();
    setMe(undefined);
  }, []);
  const reload = useCallback(() => api.get<Me>('/me').then(setMe), []);
  useEffect(() => {
    if (session.token)
      void reload()
        .catch(leave)
        .finally(() => setLoading(false));
  }, [reload, leave]);
  if (loading) return <p>Loading…</p>;
  if (!me) return <SignInPage onSignedIn={({ user }) => setMe(user)} />;
  // After account deletion the session is gone already, so a refused sign-out is fine.
  const signOut = () => api.post('/auth/logout').finally(leave);
  return (
    <SessionContext value={{ me, reload, signOut }}>
      <BrowserRouter>
        <LiveProvider onSignedOut={leave}>
          <Layout />
        </LiveProvider>
      </BrowserRouter>
    </SessionContext>
  );
}

function Layout() {
  const { me, reload, signOut } = useSession();
  const notifications = useResource<Notification[]>('/notifications');
  useLive(`user:${me.id}`, () => {
    void notifications.reload();
    void reload();
  });
  const unread = notifications.data?.filter((n) => n.read_at === null).length ?? 0;
  const links: [string, string][] = [
    ['/', 'Home'],
    ['/communities', 'Communities'],
    ['/people', 'People'],
    ['/messages', 'Messages'],
    ['/drafts', 'Drafts'],
    ['/notifications', `Notifications${unread ? ` (${unread})` : ''}`],
    ['/settings', 'Settings'],
    ...(me.role === 'moderator' ? [['/moderation', 'Moderation'] as [string, string]] : []),
    ...(me.role === 'admin' ? [['/admin', 'Admin'] as [string, string]] : []),
  ];
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="top">
        <strong>Connect</strong>
        <nav aria-label="Main">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'}>
              {label}
            </NavLink>
          ))}
        </nav>
        <span>
          {me.display_name}{' '}
          <button type="button" className="quiet" onClick={signOut}>
            Sign out
          </button>
        </span>
      </header>
      <main id="main">
        {me.muted_until && (
          <p className="banner warning">
            You are muted until {new Date(me.muted_until).toLocaleString('en-GB')} and can only
            read.
          </p>
        )}
        <Routes>
          <Route path="/" element={<FeedPage />} />
          <Route path="/posts/:id" element={<PostPage />} />
          <Route path="/communities" element={<CommunitiesPage />} />
          <Route path="/communities/:id" element={<CommunityPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/users/:id" element={<ProfilePage />} />
          <Route path="/messages/:id?" element={<MessagesPage />} />
          <Route path="/drafts" element={<DraftsPage />} />
          <Route path="/drafts/:id" element={<DraftPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/moderation" element={<ModerationPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<ErrorNote message="Page not found." />} />
        </Routes>
      </main>
    </>
  );
}
