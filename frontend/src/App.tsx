import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import {
  Activity,
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  BarChart3,
  BookOpen,
  ChevronDown,
  CircleHelp,
  CloudUpload,
  FileText,
  LogOut,
  LayoutDashboard,
  Menu,
  Plus,
  Settings,
  ShieldCheck,
  Target,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { api, Game, MoveRow } from "./api";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
const sample =
  '[Event "Casual Game"]\n[Site "Local"]\n[Date "2026.11.24"]\n[White "Mira Chen"]\n[Black "You"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 *';
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

function Auth({ onAuth, message }: { onAuth: () => void; message: string }) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const googleButton = useRef<HTMLDivElement>(null);
  const [email, setEmail] = useState(""), [password, setPassword] = useState("");
  const [error, setError] = useState(""), [busy, setBusy] = useState(false), [linkChallenge, setLinkChallenge] = useState("");
  const [legacyLinkRequired, setLegacyLinkRequired] = useState(false);
  const [credential, setCredential] = useState("");
  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;
    const setup = () => {
      if (cancelled || !window.google || !googleButton.current) return;
      window.google.accounts.id.initialize({ client_id: clientId, callback: async ({ credential }) => {
        setBusy(true); setError("");
        try {
          if (linkChallenge) setCredential(credential);
          await api.post("/v1/auth/google", { credential, ...(linkChallenge ? { link_challenge: linkChallenge } : {}) });
          setLinkChallenge(""); setCredential(""); setLegacyLinkRequired(false); onAuth();
        }
        catch (e: any) {
          const detail = e.response?.data?.detail;
          if (detail?.code === "legacy_account_link_required") { setLegacyLinkRequired(true); setError(detail.message); }
          else if (detail?.code === "google_email_mismatch") { setError(detail.message); setLinkChallenge(""); }
          else setError(typeof detail === "string" ? detail : detail?.message || "Google sign-in failed. Please try again.");
        } finally { setBusy(false); }
      }});
      googleButton.current.replaceChildren();
      window.google.accounts.id.renderButton(googleButton.current, { theme: "outline", size: "large", shape: "rectangular", text: "continue_with", width: 320 });
    };
    if (window.google) setup();
    else {
      let script = document.querySelector<HTMLScriptElement>('script[data-google-identity="true"]');
      if (!script) { script = document.createElement("script"); script.src = "https://accounts.google.com/gsi/client"; script.async = true; script.defer = true; script.dataset.googleIdentity = "true"; document.head.appendChild(script); }
      script.addEventListener("load", setup); if (window.google) setup();
    }
    return () => { cancelled = true; };
  }, [clientId, linkChallenge]);
  async function startLink(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const { data } = await api.post("/v1/auth/link/legacy", { email, password });
      const challenge = data.link_challenge;
      const currentCredential = credential;
      setLinkChallenge(challenge); setPassword("");
      if (!currentCredential) { setError("Account verified. Choose the matching Google account to finish linking."); window.google?.accounts.id.prompt(); return; }
      const completed = await api.post("/v1/auth/google", {credential:currentCredential, link_challenge:challenge});
      setCredential(""); setLinkChallenge(""); setLegacyLinkRequired(false);
      if (!completed.data?.user) throw new Error("The session could not be created");
      onAuth();
    }
    catch (e: any) { setError(typeof e.response?.data?.detail === "string" ? e.response.data.detail : e.response?.data?.detail?.message || "Could not verify the existing account."); }
    finally { setBusy(false); }
  }
  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="brand auth-brand">
          <span className="brand-mark">
            <Activity size={19} />
          </span>
          <span>
            ENDGAME<span className="brand-sub">CHESS REVIEW</span>
          </span>
        </div>
        <div className="eyebrow">YOUR PRIVATE CHESS WORKSPACE</div>
        <h1>Welcome to your chess review</h1>
        <p>Review your games with clear, local Stockfish analysis.</p>
        {message && <div className="auth-error">{message}</div>}
        {!clientId ? <div className="auth-error">Google sign-in needs a client ID. Set GOOGLE_CLIENT_ID and VITE_GOOGLE_CLIENT_ID in your local .env file.</div> : <div ref={googleButton} className="google-signin" />}
        {error && <div className="auth-error">{error}</div>}
        {linkChallenge && <button type="button" className="primary auth-submit" disabled={busy} onClick={() => { setError("Choose the Google account that uses the same email as your existing account."); window.google?.accounts.id.prompt(); }}>{busy ? "Please wait…" : "Continue with Google to finish linking"}</button>}
        {legacyLinkRequired || linkChallenge ? (
        <form onSubmit={startLink}>
          <label>
            Existing account email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={1}
              autoComplete="current-password"
            />
          </label>
          <button className="primary auth-submit" disabled={busy || !!linkChallenge}>
            {busy ? "Please wait…" : linkChallenge ? "Account verified" : "Verify existing account"}{" "}
            <ArrowRight size={15} />
          </button>
        </form>
        ) : null}
        <div className="auth-privacy">
          <ShieldCheck size={14} /> Your games and analysis stay in your
          workspace.
        </div>
      </div>
    </div>
  );
}
function SettingsPage({connected, username, setUsername, status, setStatus, onConnected}: {connected: boolean; username: string; setUsername: (value: string) => void; status: string; setStatus: (value: string) => void; onConnected: () => void}) {
  const [prefs, setPrefs] = useState({default_analysis_depth:16, multipv:3, auto_analyze:false, auto_sync:true});
  useEffect(() => { api.get("/v1/users/preferences").then(({data}) => setPrefs(data.preferences)).catch(() => {}); }, []);
  return <section className="page"><div className="page-heading"><div><div className="eyebrow">PREFERENCES</div><h1>Settings</h1><p>Engine preferences and Chess.com imports.</p></div></div><div className="panel settings-card"><h2>Engine preferences</h2><label>Default depth<input type="number" min={8} max={30} value={prefs.default_analysis_depth} onChange={e => setPrefs({...prefs, default_analysis_depth:Number(e.target.value)})} /></label><label>Principal variations<input type="number" min={1} max={5} value={prefs.multipv} onChange={e => setPrefs({...prefs, multipv:Number(e.target.value)})} /></label><label className="checkbox-label"><input type="checkbox" checked={prefs.auto_analyze} onChange={e => setPrefs({...prefs, auto_analyze:e.target.checked})} /> Analyze imported games automatically</label><label className="checkbox-label"><input type="checkbox" checked={prefs.auto_sync} onChange={e => setPrefs({...prefs, auto_sync:e.target.checked})} /> Sync Chess.com every 12 hours</label><button className="primary" onClick={async () => { try { await api.patch("/v1/users/preferences", prefs); setStatus("Preferences saved."); } catch {setStatus("Could not save preferences.");} }}>Save preferences</button><h2>Chess.com account</h2>{connected ? <p>Chess.com account connected.</p> : <label>Chess.com username<input value={username} onChange={e => setUsername(e.target.value)} placeholder="username" /></label>}{!connected && <button className="primary" onClick={async () => { setStatus("Connecting…"); try { await api.post("/v1/integrations/chesscom", {username}); onConnected(); setStatus("Connected successfully."); } catch(e: any) { setStatus(e.response?.data?.detail || "Could not connect account."); } }}>Connect account</button>}{connected && <button className="primary" onClick={async () => { try { const {data} = await api.post("/v1/integrations/chesscom/sync", {sync_mode:"initial"}); setStatus(`Sync started (${data.id}). Refresh the game list in a moment.`); } catch(e: any) { setStatus(e.response?.data?.detail || "Could not start sync."); } }}>Import recent 3 months</button>}{status && <p>{status}</p>}</div></section>;
}

function ProfileEditor({onSaved}: {onSaved: (name: string) => void}) {
  const [name, setName] = useState(""), [country, setCountry] = useState(""), [bio, setBio] = useState(""), [status, setStatus] = useState("");
  useEffect(() => { api.get("/v1/users/profile").then(({data}) => {setName(data.profile.display_name || ""); setCountry(data.profile.country || ""); setBio(data.profile.bio || "");}).catch(() => setStatus("Could not load profile.")); }, []);
  return <div className="panel settings-card"><label>Display name<input value={name} onChange={e => setName(e.target.value)} maxLength={100} /></label><label>Country<input value={country} onChange={e => setCountry(e.target.value)} maxLength={100} /></label><label>Bio<textarea value={bio} onChange={e => setBio(e.target.value)} maxLength={1000} /></label><button className="primary" onClick={async () => { try { await api.patch("/v1/users/profile", {display_name:name, country, bio}); onSaved(name); setStatus("Profile saved."); } catch {setStatus("Could not save profile.");} }}>{"Save profile"}</button>{status && <p>{status}</p>}</div>;
}

function Dashboard({
  games,
  onImport,
  onSelect,
}: {
  games: Game[];
  onImport: () => void;
  onSelect: (id: string) => void;
}) {
  const [averageAccuracy, setAverageAccuracy] = useState<number | null>(null);
  useEffect(() => { api.get("/v1/analytics").then(({data}) => setAverageAccuracy(data.average_accuracy)).catch(() => {}); }, []);
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">MONDAY, NOVEMBER 24, 2026</div>
          <h1>
            Your chess, <em>in focus.</em>
          </h1>
          <p>A clear view of your progress, one move at a time.</p>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> Review a game
        </button>
      </div>
      <section className="stats-grid">
        <Stat
          icon={<BookOpen />}
          label="Games reviewed"
          value={String(games.length).padStart(2, "0")}
          change="Your full archive"
        />
        <Stat
          icon={<Target />}
          label="Wins"
          value={String(
            games.filter((g) => g.result === "1-0").length,
          ).padStart(2, "0")}
          change="Keep building momentum"
        />
        <Stat
          icon={<ArrowLeftRight />}
          label="Draws"
          value={String(
            games.filter((g) => g.result === "1/2-1/2").length,
          ).padStart(2, "0")}
          change="Hard fought games"
        />
        <Stat
          icon={<Activity />}
          label="Average accuracy"
          value={averageAccuracy == null ? "—" : `${averageAccuracy}%`}
          change="Average across analyzed games"
        />
      </section>
      <section className="panel recent-panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">YOUR LIBRARY</div>
            <h2>Recent games</h2>
          </div>
          <Link className="text-link" to="/games">
            View all games <ArrowRight size={15} />
          </Link>
        </div>
        {games.length ? (
          <div className="game-table">
            <div className="table-row table-labels">
              <span>GAME</span>
              <span>RESULT</span>
              <span>MOVES</span>
              <span>DATE</span>
              <span></span>
            </div>
            {games.slice(0, 6).map((g) => (
              <div
                className="table-row"
                key={g.id}
                onClick={() => onSelect(g.id)}
              >
                <span className="game-names">
                  <i className="piece-dot">♞</i>
                  <span>
                    <b>{g.white_player}</b>
                    <small>vs {g.black_player}</small>
                  </span>
                </span>
                <span className="result-chip">{g.result}</span>
                <span>{g.move_count}</span>
                <span>{g.played_at || "—"}</span>
                <span>
                  <ArrowRight size={16} />
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty">
            <div className="empty-icon">
              <FileText />
            </div>
            <h3>A fresh board awaits</h3>
            <p>
              Import a PGN and start understanding the moments that shaped your
              games.
            </p>
            <button className="secondary" onClick={onImport}>
              <Upload size={16} /> Import your first game
            </button>
          </div>
        )}
      </section>
      <div className="bottom-grid">
        <section className="panel insight">
          <div className="eyebrow">YOUR NEXT STEP</div>
          <h2>Build a clearer picture.</h2>
          <p>
            Analyze a game to see your move quality, key turning points and the
            lines you missed.
          </p>
          <button className="quiet" onClick={onImport}>
            Get started <ArrowRight size={15} />
          </button>
        </section>
        <section className="panel engine-card">
          <span className="engine-icon">
            <ShieldCheck />
          </span>
          <div>
            <div className="eyebrow">LOCAL ENGINE</div>
            <h3>Private by design</h3>
            <p>
              Stockfish analysis runs on your own machine. Your games stay
              yours.
            </p>
          </div>
          <span className="green-dot" />
        </section>
      </div>
    </div>
  );
}
function StatisticsPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { Promise.all([api.get("/v1/analytics"), api.get("/v1/analytics/performance")]).then(([summary, performance]) => setData({...summary.data, ...performance.data})).catch(() => setData({error:"Could not load statistics."})); }, []);
  return <section className="page"><div className="page-heading"><div><div className="eyebrow">YOUR PROGRESS</div><h1>Statistics</h1><p>Results, review coverage, and your game patterns.</p></div></div>{data?.error ? <div className="auth-error">{data.error}</div> : <><section className="stats-grid"><Stat icon={<BookOpen />} label="Total games" value={String(data?.total_games ?? "—")} change="In your library" /><Stat icon={<Activity />} label="Reviewed games" value={String(data?.reviewed_games ?? "—")} change="With completed analysis" /><Stat icon={<Target />} label="Average accuracy" value={data?.average_accuracy == null ? "—" : `${data.average_accuracy}%`} change="From completed reviews" /><Stat icon={<ArrowLeftRight />} label="Wins / draws / losses" value={data ? `${data.results.wins} / ${data.results.draws} / ${data.results.losses}` : "—"} change="Your results" /></section><section className="panel settings-card"><h2>Monthly performance</h2>{(data?.monthly || []).length ? data.monthly.map((row: any) => <div className="stat-change" key={row.month}>{row.month}: {row.games} games · {row.wins} wins · {row.draws} draws · {row.losses} losses</div>) : <p>Monthly performance will appear after you import games.</p>}<h2>Most frequent opponents</h2>{(data?.opponents || []).length ? data.opponents.map((row: any) => <div className="stat-change" key={row.name}>{row.name} · {row.games} games</div>) : <p>Opponent data will appear with your game history.</p>}<h2>Openings</h2>{(data?.openings || []).length ? data.openings.map((row: any) => <div className="stat-change" key={row.name}>{row.name} · {row.count}</div>) : <p>Opening data will appear when it is available in PGN headers.</p>}</section></>}</section>;
}

function Stat({
  icon,
  label,
  value,
  change,
}: {
  icon: any;
  label: string;
  value: string;
  change: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        {icon}
        <span>{label}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-change">{change}</div>
    </div>
  );
}
function Games({
  games,
  onImport,
  onSelect,
  onDelete,
}: {
  games: Game[];
  onImport: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [resultFilter, setResultFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const filtered = games.filter((game) => {
    const matchesText = !query || `${game.white_player} ${game.black_player} ${game.event} ${game.opening_name || ""}`.toLowerCase().includes(query.toLowerCase());
    const userResult = game.result === "1/2-1/2" ? "draw" : ((game.user_color === "white" && game.result === "1-0") || (game.user_color === "black" && game.result === "0-1")) ? "win" : ((game.user_color === "white" && game.result === "0-1") || (game.user_color === "black" && game.result === "1-0")) ? "loss" : "unknown";
    return matchesText && (!resultFilter || userResult === resultFilter) && (!sourceFilter || (game.source || "pgn") === sourceFilter);
  });
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">GAME LIBRARY</div>
          <h1>Your games</h1>
          <p>Every game is a chance to see something new.</p>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> Import game
        </button>
      </div>
      <section className="panel recent-panel">
  <div className="game-filters"><input aria-label="Search games" placeholder="Search player, opening, event" value={query} onChange={e => setQuery(e.target.value)} /><select value={resultFilter} onChange={e => setResultFilter(e.target.value)}><option value="">All results</option><option value="win">Wins</option><option value="draw">Draws</option><option value="loss">Losses</option></select><select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}><option value="">All sources</option><option value="pgn">PGN import</option><option value="chesscom">Chess.com</option></select></div>
  <div className="panel-head">
    <div>
      <div className="eyebrow">ARCHIVE</div>
      <h2>{filtered.length} games</h2>
    </div>
  </div>
  {filtered.length ? (
    <div className="game-table">
      <div className="table-row table-labels">
        <span>GAME</span>
        <span>RESULT</span>
        <span>MOVES</span>
        <span>DATE</span>
        <span />
      </div>
      {filtered.map((g) => (
        <div
          className="table-row"
          key={g.id}
          onClick={() => onSelect(g.id)}
        >
          <span className="game-names">
            <i className="piece-dot">♞</i>
            <span>
              <b>{g.white_player}</b>
              <small>vs {g.black_player}</small>
            </span>
          </span>
          <span className="result-chip">{g.result}</span>
          <span>{g.move_count}</span>
          <span>{g.played_at || "—"}</span>
          <button
            className="icon-btn delete"
            title="Delete game"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(g.id);
            }}
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
    </div>
  ) : (
    <div className="empty">
      <h3>No games yet</h3>
      <p>Import your first PGN game to begin.</p>
      <button className="secondary" onClick={onImport}>
        <Upload size={16} /> Import PGN
      </button>
    </div>
  )}
</section>
    </div>
  );
}
function Review({ onLoad }: { onLoad: (id: string) => Promise<Game> }) {
  const { id } = useParams();
  const [game, setGame] = useState<Game | null>(null),
    [idx, setIdx] = useState(0),
    [err, setErr] = useState(""),
    [job, setJob] = useState<any>(null),
    [orientation, setOrientation] = useState<"white" | "black">("white");
  const [explorationBoard, setExplorationBoard] = useState<Chess | null>(null);
  const [explorationAnalysis, setExplorationAnalysis] = useState<any>(null);
  const [explorationPending, setExplorationPending] = useState(false);
  const [explorationError, setExplorationError] = useState("");
  const [boardWidth, setBoardWidth] = useState(620);
  const boardShellRef = useRef<HTMLDivElement>(null);
  const explorationRequest = useRef(0);
  useEffect(() => {
    if (id)
      onLoad(id)
        .then(setGame)
        .catch((e) =>
          setErr(e.response?.data?.detail || "Unable to load this game"),
        );
  }, [id]);
  useEffect(() => {
    const element = boardShellRef.current;
    if (!element) return;
    const measure = () => setBoardWidth(Math.max(200, Math.min(620, element.clientWidth - 45)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [game]);
  useEffect(() => {
    explorationRequest.current += 1;
    setExplorationBoard(null);
    setExplorationAnalysis(null);
    setExplorationPending(false);
    setExplorationError("");
  }, [idx]);
  useEffect(() => {
    if (!job?.id || ["completed", "failed"].includes(job.status)) return;
    const t = setInterval(
      () =>
        api
          .get(`/analysis-jobs/${job.id}`)
          .then(async (r) => {
            setJob(r.data);
            if (r.data.status === "completed" && id) onLoad(id).then(setGame);
          })
          .catch(() => {}),
      1800,
    );
    return () => clearInterval(t);
  }, [job?.id, job?.status, id]);
  useEffect(() => {
    const onArrow = (event: KeyboardEvent) => {
      if (
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIdx((current) => Math.max(0, current - 1));
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setIdx((current) => Math.min(game?.moves.length ?? 0, current + 1));
      }
    };
    window.addEventListener("keydown", onArrow);
    return () => window.removeEventListener("keydown", onArrow);
  }, [game?.moves.length]);
  const board = useMemo(() => {
    if (!game) return new Chess();
    const c = new Chess(game.initial_fen);
    for (let i = 0; i < idx; i++) {
      try {
        c.move(game.moves[i].san);
      } catch {}
    }
    return c;
  }, [game, idx]);
  if (err)
    return (
      <div className="page">
        <div className="empty">
          <h3>Could not load this game</h3>
          <p>{err}</p>
          <Link to="/games" className="secondary">
            Back to games
          </Link>
        </div>
      </div>
    );
  if (!game)
    return (
      <div className="page">
        <div className="loading">Opening your game…</div>
      </div>
    );
  const selected = game.moves[idx - 1];
  const evaluation = idx === 0
    ? game.moves[0]?.analysis?.evaluation_before ?? null
    : game.moves[idx - 1]?.analysis
      ? (game.moves[idx - 1].color === "white" ? 1 : -1) * game.moves[idx - 1].analysis!.evaluation_after
      : null;
  const evaluationLabel = evaluation === null
    ? "—"
    : `${evaluation >= 0 ? "+" : "−"}${Math.min(Math.abs(evaluation), 99.9).toFixed(1)}`;
  let bestMoveSan = selected?.analysis?.best_move_uci ?? null;
  if (selected?.analysis?.best_move_uci) {
    try {
      const beforeSelected = new Chess(board.fen());
      beforeSelected.undo();
      const uci = selected.analysis.best_move_uci;
      const bestMove = beforeSelected.move({
        from: uci.slice(0, 2),
        to: uci.slice(2, 4),
        promotion: uci[4],
      });
      bestMoveSan = bestMove.san;
    } catch {
      // Keep the UCI move available if it cannot be converted to SAN.
    }
  }
  const playedBestMove = selected?.uci === selected?.analysis?.best_move_uci;
  const shownBoard = explorationBoard ?? board;
  const currentBestMove = explorationBoard
    ? explorationAnalysis?.best_move_uci
    : game.moves[idx]?.analysis?.best_move_uci;
  const customArrows = currentBestMove
    ? [[currentBestMove.slice(0, 2), currentBestMove.slice(2, 4), "#e6b85c"] as [string, string, string]]
    : [];
  const shownEvaluation = explorationBoard
    ? explorationAnalysis?.evaluation ?? null
    : evaluation;
  const shownEvaluationLabel = explorationBoard && explorationPending
    ? "…"
    : shownEvaluation === null
      ? "—"
      : `${shownEvaluation >= 0 ? "+" : "−"}${Math.min(Math.abs(shownEvaluation), 99.9).toFixed(1)}`;
  const shownWhiteAdvantage = shownEvaluation === null
    ? 50
    : 50 + Math.tanh(shownEvaluation / 4) * 50;
  function exploreMove(from: string, to: string) {
    const next = new Chess(shownBoard.fen());
    try {
      const movingPiece = next.get(from as any);
      const promotion = movingPiece?.type === "p" && (to[1] === "1" || to[1] === "8") ? "q" : undefined;
      next.move({ from, to, promotion });
    } catch {
      return false;
    }
    setExplorationBoard(next);
    setExplorationAnalysis(null);
    setExplorationPending(true);
    setExplorationError("");
    const requestId = ++explorationRequest.current;
    api.post(`/games/${id}/position-analysis`, { fen: next.fen() })
      .then(({ data }) => {
        if (requestId !== explorationRequest.current) return;
        setExplorationAnalysis(data);
        setExplorationPending(false);
      })
      .catch((error) => {
        if (requestId !== explorationRequest.current) return;
        setExplorationPending(false);
        setExplorationError(error.response?.data?.detail || "Position analysis failed");
      });
    return true;
  }
  const evalPoints = game.moves
    .filter((m) => m.analysis)
    .map((m) => ({
      ply: m.ply,
      score:
        m.color === "white"
          ? m.analysis!.evaluation_after
          : -m.analysis!.evaluation_after,
    }));
  async function analyze() {
    try {
      const { data } = await api.post(`/games/${id}/analysis`);
      setJob(data);
    } catch (e: any) {
      setJob({
        status: "failed",
        error:
          e.response?.data?.detail ||
          "Unable to start Stockfish. Check the worker and engine setup.",
      });
    }
  }
  return (
    <div className="page review-page">
      <div className="review-top">
        <Link to="/games" className="back-link">
          <ArrowLeft size={15} /> All games
        </Link>
        <div className="review-title">
          <div>
            <div className="eyebrow">GAME REVIEW</div>
            <h1>
              {game.white_player} <span>vs</span> {game.black_player}
            </h1>
            <p>
              {game.event} <span>·</span> {game.played_at || "Date unknown"}{" "}
              <span>·</span> {game.result}
            </p>
          </div>
          <button
            className="primary"
            onClick={analyze}
            disabled={job?.status === "queued" || job?.status === "running"}
          >
            <Activity size={16} />
            {job?.status === "queued" || job?.status === "running"
              ? "Analysis queued"
              : game.analysis_summary || job?.status === "completed"
                ? "Reanalyze game"
                : "Analyze game"}
          </button>
        </div>
      </div>
      <div className="review-layout">
        <section className="board-area">
          <div className="board-meta">
            <span className="side-tag">
              <i className={orientation === "black" ? "white-dot" : ""} />
              {orientation === "white" ? game.black_player : game.white_player}
              <small>({orientation === "white" ? "Black" : "White"})</small>
            </span>
            <button
              className="flip-control"
              onClick={() => setOrientation((current) => current === "white" ? "black" : "white")}
              aria-label="Flip board orientation"
              title="Flip board"
            >
              <ArrowLeftRight size={14} /> Flip board
            </button>
          </div>
          <div className="board-shell" ref={boardShellRef}>
            <div className="eval-track" title="Evaluation from White’s perspective">
              <span className="eval-readout">{shownEvaluationLabel}</span>
              <div className="eval-bar">
                <span style={{ height: `${shownWhiteAdvantage}%` }} />
              </div>
            </div>
            <div className="chessboard">
              <Chessboard
                position={shownBoard.fen()}
                boardOrientation={orientation}
                arePiecesDraggable={true}
                onPieceDrop={exploreMove}
                boardWidth={boardWidth}
                promotionDialogVariant="vertical"
                customArrows={customArrows as any}
                customDarkSquareStyle={{ backgroundColor: "#718b76" }}
                customLightSquareStyle={{ backgroundColor: "#e8e3d5" }}
              />
            </div>
          </div>
          {explorationBoard && (
            <div className="explore-status" aria-live="polite">
              {explorationPending ? "Analyzing this position…" : explorationError || "Exploration position · drag another piece to continue"}
              <button className="text-link" onClick={() => {
                explorationRequest.current += 1;
                setExplorationBoard(null);
                setExplorationAnalysis(null);
                setExplorationPending(false);
                setExplorationError("");
              }}>Return to game</button>
            </div>
          )}
          <div className="board-meta">
            <span className="side-tag">
              <i className={orientation === "white" ? "white-dot" : ""} />
              {orientation === "white" ? game.white_player : game.black_player}{" "}
              <small>({orientation === "white" ? "White" : "Black"})</small>
            </span>
            <span className="rating-placeholder">—</span>
          </div>
          <div className="board-controls">
            <button
              className="control-btn"
              onClick={() => setIdx(0)}
              title="Start"
            >
              |◀
            </button>
            <button
              className="control-btn"
              onClick={() => setIdx((current) => Math.max(0, current - 1))}
              disabled={idx === 0}
              title="Previous move (←)"
              aria-label="Previous move"
            >
              ◀
            </button>
            <span>
              {idx === 0
                ? "Starting position"
                : `After ${game.moves[idx - 1].san} · ${Math.ceil(idx / 2)}.${idx % 2 ? " Black" : " White"} to move`}
            </span>
            <button
              className="control-btn"
              onClick={() => setIdx((current) => Math.min(game.moves.length, current + 1))}
              disabled={idx === game.moves.length}
              title="Next move (→)"
              aria-label="Next move"
            >
              ▶
            </button>
            <button
              className="control-btn"
              onClick={() => setIdx(game.moves.length)}
              title="End"
            >
              ▶|
            </button>
          </div>
          <div className="panel eval-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">POSITION EVALUATION</div>
                <h3>Evaluation over time</h3>
              </div>
              <span className="depth-tag">
                {selected?.analysis
                  ? `Depth ${job?.depth || "—"}`
                  : evalPoints.length
                    ? "Analysis complete"
                    : "Analysis needed"}
              </span>
            </div>
            {evalPoints.length ? (
              <ResponsiveContainer width="100%" height={120}>
                <LineChart
                  data={evalPoints}
                  margin={{ top: 10, right: 8, left: -22, bottom: 0 }}
                >
                  <CartesianGrid stroke="#29332f" strokeDasharray="3 4" />
                  <XAxis
                    dataKey="ply"
                    tick={{ fill: "#75827c", fontSize: 9 }}
                    tickLine={false}
                    axisLine={{ stroke: "#39443e" }}
                  />
                  <YAxis
                    tick={{ fill: "#75827c", fontSize: 9 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#151e19",
                      border: "1px solid #38483d",
                      borderRadius: 5,
                      fontSize: 10,
                    }}
                    formatter={(v: number) => [
                      `${v > 0 ? "+" : ""}${v.toFixed(2)}`,
                      "White eval",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#9cbea2"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">
                Evaluation chart appears after a game is analyzed.
              </div>
            )}
          </div>
        </section>
        <aside className="review-side">
          <div className="panel moves-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">MOVES</div>
                <h3>
                  Move list{" "}
                  <span className="muted">({game.moves.length} plies)</span>
                </h3>
              </div>
              <button className="icon-btn">
                <ChevronDown size={16} />
              </button>
            </div>
            <div className="moves-list">
              {Array.from(
                { length: Math.ceil(game.moves.length / 2) },
                (_, row) => {
                  const w = game.moves[row * 2],
                    b = game.moves[row * 2 + 1];
                  return (
                    <div className="move-row" key={row}>
                      <span className="move-no">{row + 1}.</span>
                      <button
                        className={idx === w.ply ? "move-san active" : ""}
                        title={w.analysis ? `${w.san} · ${w.analysis.classification}` : w.san}
                        onClick={() => setIdx(w.ply)}
                      >
                        {w.san}
                        {w.analysis && (
                          <span className={`move-quality-label ${w.analysis.classification.toLowerCase()}`}>
                            {w.analysis.classification}
                          </span>
                        )}
                      </button>
                      {b && (
                        <button
                          className={idx === b.ply ? "move-san active" : ""}
                          title={b.analysis ? `${b.san} · ${b.analysis.classification}` : b.san}
                          onClick={() => setIdx(b.ply)}
                        >
                          {b.san}
                          {b.analysis && (
                            <span className={`move-quality-label ${b.analysis.classification.toLowerCase()}`}>
                              {b.analysis.classification}
                            </span>
                          )}
                        </button>
                      )}
                    </div>
                  );
                },
              )}
            </div>
            <div className="move-legend">
              {["Book", "Brilliant", "Great", "Best", "Excellent", "Good", "Miss", "Inaccuracy", "Mistake", "Blunder"].map((label) => (
                <span key={label}>
                  <i className={`quality ${label.toLowerCase()}`} /> {label}
                </span>
              ))}
            </div>
          </div>
          <div className="panel engine-analysis">
            <div className="engine-head">
              <span className="engine-icon small-engine">
                <Activity size={16} />
              </span>
              <div>
                <div className="eyebrow">STOCKFISH</div>
                <h3>Engine analysis</h3>
              </div>
              <span className="green-dot" />
            </div>
            {job && (
              <div className="job-state">
                {job.status === "queued"
                  ? "Analysis queued · starting shortly…"
                  : job.status === "running"
                    ? job.progress
                      ? `Analyzing · ${job.progress}%`
                      : "Starting Stockfish…"
                    : job.status === "completed"
                      ? "Analysis complete"
                      : job.error || job.error_message}
              </div>
            )}
            <div className="analysis-content">
              {explorationBoard ? (
                explorationPending ? (
                  <div className="analysis-empty">Stockfish is evaluating your position…</div>
                ) : explorationError ? (
                  <div className="analysis-empty">{explorationError}</div>
                ) : explorationAnalysis ? (
                  <>
                    <div className="eval-score">
                      {shownEvaluationLabel}
                      <span>White eval · explored position</span>
                    </div>
                    <div className="best-move missed-best">
                      <div className="move-comparison-side recommended">
                        <span>STOCKFISH BEST · FOLLOW THE ARROW</span>
                        <b>{explorationAnalysis.best_move_uci || "Game over"}</b>
                      </div>
                    </div>
                    <div className="pv">
                      <span>PRINCIPAL VARIATION</span>
                      <b>{explorationAnalysis.principal_variation?.join(" ") || "—"}</b>
                    </div>
                  </>
                ) : (
                  <div className="analysis-empty">Make a legal move to analyze this position.</div>
                )
              ) : selected?.analysis ? (
                <>
                  <div className="eval-score">
                    {evaluationLabel}
                    <span>White eval after {selected.san}</span>
                  </div>
                  <div className={`best-move ${playedBestMove ? "played-best" : "missed-best"}`}>
                    <div className="move-comparison-side">
                      <span>PLAYED</span>
                      <b>{selected.san}</b>
                    </div>
                    {!playedBestMove && (
                      <>
                        <ArrowRight size={14} />
                        <div className="move-comparison-side recommended">
                          <span>STOCKFISH BEST</span>
                          <b>{bestMoveSan || "—"}</b>
                        </div>
                      </>
                    )}
                    <i
                      className={`quality ${selected.analysis.classification.toLowerCase()}`}
                    />
                    <small>{playedBestMove ? "Best move" : selected.analysis.classification}</small>
                  </div>
                  <div className="pv">
                    <span>PRINCIPAL VARIATION</span>
                    <b>
                      {selected.analysis.principal_variation.join(" ") || "—"}
                    </b>
                  </div>
                </>
              ) : (
                <div className="analysis-empty">
                  <span className="analysis-spark">✳</span>
                  <p>
                    {job?.status === "completed"
                      ? "Select a move to inspect its evaluation and best continuation."
                      : "Run Stockfish to uncover the best lines and turning points in this game."}
                  </p>
                  {(!job || job.status === "failed") && (
                    <button className="secondary full" onClick={analyze}>
                      <Activity size={15} /> Start analysis
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="accuracy-panel">
            <div className="accuracy-heading">
              <span>PLAYER ACCURACY</span>
              {!game.analysis_summary && <small>Available after analysis completes</small>}
            </div>
            <div>
              <span>WHITE ACCURACY</span>
              <b>
                {game.analysis_summary?.accuracy_white == null
                  ? "—"
                  : `${game.analysis_summary.accuracy_white}%`}
              </b>
            </div>
            <div>
              <span>BLACK ACCURACY</span>
              <b>
                {game.analysis_summary?.accuracy_black == null
                  ? "—"
                  : `${game.analysis_summary.accuracy_black}%`}
              </b>
            </div>
            <p>
              Review scores summarize move quality and are not official chess
              ratings.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
function ImportModal({
  onClose,
  onImport,
  loading,
}: {
  onClose: () => void;
  onImport: (p: string) => void;
  loading: boolean;
}) {
  const [text, setText] = useState(sample),
    [tab, setTab] = useState("paste"),
    [fileName, setFileName] = useState("");
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-heading">
          <div>
            <div className="eyebrow">ADD TO YOUR LIBRARY</div>
            <h2>Bring in a game</h2>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X />
          </button>
        </div>
        <p className="modal-intro">
          Paste a PGN or upload a file. We’ll check the moves before saving.
        </p>
        <div className="tabs">
          <button
            className={tab === "paste" ? "selected" : ""}
            onClick={() => setTab("paste")}
          >
            <FileText size={15} /> Paste PGN
          </button>
          <button
            className={tab === "upload" ? "selected" : ""}
            onClick={() => setTab("upload")}
          >
            <CloudUpload size={15} /> Upload file
          </button>
        </div>
        {tab === "paste" ? (
          <textarea
            className="pgn-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              '[Event "Casual Game"]\n[White "Player 1"]\n[Black "Player 2"]\n\n1. e4 e5 ...'
            }
          />
        ) : (
          <label className="file-drop">
            <input
              type="file"
              accept=".pgn,.txt"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFileName(f.name);
                  setText(await f.text());
                }
              }}
            />
            <CloudUpload size={25} />
            <b>{fileName || "Choose a PGN file"}</b>
            <span>PGN or TXT, up to 500 KB</span>
          </label>
        )}
        <div className="modal-footer">
          <span>
            <ShieldCheck size={15} /> Your games stay private
          </span>
          <button
            className="primary"
            disabled={loading || !text.trim()}
            onClick={() => onImport(text)}
          >
            {loading ? "Validating…" : "Import game"} <ArrowRight size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
export default App;
