import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Activity, BarChart3, BookOpen, ChevronDown, CircleHelp, LayoutDashboard, LogOut, Menu, Plus, Settings, ShieldCheck } from "lucide-react";
import { api, Game } from "./api";
import { Auth } from "./components/Auth";
import { ImportModal } from "./components/ImportModal";
import { Dashboard } from "./pages/DashboardPage";
import { Games } from "./pages/GamesPage";
import { ProfileEditor } from "./pages/ProfilePage";
import { Review } from "./pages/ReviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StatisticsPage } from "./pages/StatisticsPage";

function App() {
  const [games, setGames] = useState<Game[]>([]),
    [active, setActive] = useState<Game | null>(null),
    [loading, setLoading] = useState(false),
    [importOpen, setImportOpen] = useState(false),
    [notice, setNotice] = useState(""),
    [authMessage, setAuthMessage] = useState(""),
    [authenticated, setAuthenticated] = useState(false),
    [authChecking, setAuthChecking] = useState(true),
    [currentUser, setCurrentUser] = useState<{ display_name: string; email: string } | null>(null),
    [chessComUsername, setChessComUsername] = useState(""),
    [chessComStatus, setChessComStatus] = useState(""),
    [chessComConnected, setChessComConnected] = useState(false);
  const navigate = useNavigate();
  const refresh = () => api.get("/games").then((r) => setGames(r.data.items));
  useEffect(() => {
    api.get("/v1/auth/me").then(({ data }) => { if (data?.user) { setCurrentUser(data.user); setAuthenticated(true); } })
      .catch(() => setAuthenticated(false)).finally(() => setAuthChecking(false));
  }, []);
  useEffect(() => {
    const expired = () => {
      setAuthenticated(false);
      setCurrentUser(null);
      setAuthMessage("Your saved sign-in expired. Please sign in again.");
    };
    window.addEventListener("chess-auth-expired", expired);
    return () => window.removeEventListener("chess-auth-expired", expired);
  }, []);
  useEffect(() => {
    const refreshCsrf = () => { api.get("/v1/auth/me").catch(() => {}); };
    window.addEventListener("chess-csrf-refresh", refreshCsrf);
    return () => window.removeEventListener("chess-csrf-refresh", refreshCsrf);
  }, []);
  useEffect(() => {
    if (authenticated) {
      refresh().catch(() => {});
      api.get("/v1/integrations/chesscom").then(({ data }) => setChessComConnected(data.connected)).catch(() => {});
    }
  }, [authenticated]);
  const flash = (s: string) => {
    setNotice(s);
    setTimeout(() => setNotice(""), 3500);
  };
  async function importPgn(pgn: string) {
    setLoading(true);
    try {
      const { data } = await api.post("/games", { pgn });
      await refresh();
      setImportOpen(false);
      navigate(`/review/${data.id}`);
      flash("Game imported successfully");
    } catch (e: any) {
      flash(e.response?.data?.detail || "Could not import PGN");
    } finally {
      setLoading(false);
    }
  }
  if (authChecking) return <div className="auth-screen"><div className="auth-card">Checking your session…</div></div>;
  if (!authenticated)
    return (
      <Auth
        message={authMessage}
        onAuth={() => {
          api.get("/v1/auth/me").then(({ data }) => { if (!data?.user) throw new Error("No session was created"); setCurrentUser(data.user); setAuthenticated(true); setAuthMessage(""); })
            .catch(() => setAuthMessage("Signed in, but the session could not be loaded. Please try again."));
        }}
      />
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Activity size={19} />
          </span>
          <span>
            ENDGAME<span className="brand-sub">CHESS REVIEW</span>
          </span>
        </div>
        <div className="workspace">
          <div className="avatar">A</div>
          <div>
            <b>Personal workspace</b>
            <small>Free plan</small>
          </div>
          <ChevronDown size={15} />
        </div>
        <div className="nav-label">MENU</div>
        <nav>
          <NavLink to="/" end>
            <LayoutDashboard />
            Overview
          </NavLink>
          <NavLink to="/games">
            <BookOpen />
            My games<span className="nav-count">{games.length}</span>
          </NavLink>
          <NavLink to="/stats">
            <BarChart3 />
            Statistics
          </NavLink>
          <NavLink to="/settings"><Settings /> Settings</NavLink>
          <NavLink to="/profile"><ShieldCheck /> Profile</NavLink>
        </nav>
        <div className="nav-label library-label">LIBRARY</div>
        <nav>
          <a onClick={() => setImportOpen(true)}>
            <Plus />
            Import a game
          </a>
        </nav>
        <div className="sidebar-bottom">
          <a>
            <CircleHelp />
            Help center
          </a>
          <div className="profile">
            <div className="avatar">A</div>
            <div>
              <b>{currentUser?.display_name || "Player"}</b>
              <small>Account settings</small>
            </div>
            <button className="icon-btn" title="Sign out" onClick={async () => { try { await api.post("/v1/auth/logout"); } finally { setAuthenticated(false); setCurrentUser(null); } }}><LogOut size={15} /></button>
          </div>
        </div>
      </aside>
      <main className="main">
        <header>
          <button className="mobile-menu">
            <Menu />
          </button>
          <div className="crumb">
            Workspace <span>/</span> <b>Chess review</b>
          </div>
          <div className="header-actions">
            <span className="status">
              <i /> Local review
            </span>
            <button className="icon-btn">
              <CircleHelp size={17} />
            </button>
            <div className="avatar small">A</div>
          </div>
        </header>
        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                games={games}
                onImport={() => setImportOpen(true)}
                onSelect={(id) => navigate(`/review/${id}`)}
              />
            }
          />
          <Route
            path="/games"
            element={
              <Games
                games={games}
                onImport={() => setImportOpen(true)}
                onSelect={(id) => navigate(`/review/${id}`)}
                onDelete={async (id) => {
                  await api.delete(`/games/${id}`);
                  await refresh();
                  flash("Game deleted");
                }}
              />
            }
          />
          <Route
            path="/review/:id"
            element={
              <Review
                onLoad={async (id) => {
                  const { data } = await api.get(`/games/${id}`);
                  setActive(data);
                  return data as Game;
                }}
              />
            }
          />
          <Route
            path="/stats"
            element={<StatisticsPage />}
          />
          <Route path="/settings" element={<SettingsPage connected={chessComConnected} username={chessComUsername} setUsername={setChessComUsername} status={chessComStatus} setStatus={setChessComStatus} onConnected={() => setChessComConnected(true)} />} />
          <Route path="/profile" element={<section className="page"><div className="page-heading"><div><div className="eyebrow">YOUR ACCOUNT</div><h1>Profile</h1><p>{currentUser?.email}</p></div></div><ProfileEditor onSaved={(display_name) => setCurrentUser(currentUser ? {...currentUser, display_name} : null)} /></section>} />
        </Routes>
      </main>
      {importOpen && (
        <ImportModal
          onClose={() => setImportOpen(false)}
          onImport={importPgn}
          loading={loading}
        />
      )}
      {notice && <div className="toast">{notice}</div>}
    </div>
  );
}

export default App;
