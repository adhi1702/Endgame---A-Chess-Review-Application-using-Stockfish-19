import { useEffect, useState } from "react";
import { api } from "../api";

export function SettingsPage({
  connected,
  username,
  setUsername,
  status,
  setStatus,
  onConnected,
}: {
  connected: boolean;
  username: string;
  setUsername: (value: string) => void;
  status: string;
  setStatus: (value: string) => void;
  onConnected: () => void;
}) {
  const [prefs, setPrefs] = useState({
    default_analysis_depth: 16,
    multipv: 3,
    auto_analyze: false,
    auto_sync: true,
  });
  useEffect(() => {
    api
      .get("/v1/users/preferences")
      .then(({ data }) => setPrefs(data.preferences))
      .catch(() => {});
  }, []);
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">PREFERENCES</div>
          <h1>Settings</h1>
          <p>Engine preferences and Chess.com imports.</p>
        </div>
      </div>
      <div className="panel settings-card">
        <h2>Engine preferences</h2>
        <label>
          Default depth
          <input
            type="number"
            min={8}
            max={30}
            value={prefs.default_analysis_depth}
            onChange={(e) =>
              setPrefs({
                ...prefs,
                default_analysis_depth: Number(e.target.value),
              })
            }
          />
        </label>
        <label>
          Principal variations
          <input
            type="number"
            min={1}
            max={5}
            value={prefs.multipv}
            onChange={(e) =>
              setPrefs({ ...prefs, multipv: Number(e.target.value) })
            }
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={prefs.auto_analyze}
            onChange={(e) =>
              setPrefs({ ...prefs, auto_analyze: e.target.checked })
            }
          />{" "}
          Analyze imported games automatically
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={prefs.auto_sync}
            onChange={(e) =>
              setPrefs({ ...prefs, auto_sync: e.target.checked })
            }
          />{" "}
          Sync Chess.com every 12 hours
        </label>
        <button
          className="primary"
          onClick={async () => {
            try {
              await api.patch("/v1/users/preferences", prefs);
              setStatus("Preferences saved.");
            } catch {
              setStatus("Could not save preferences.");
            }
          }}
        >
          Save preferences
        </button>
        <h2>Chess.com account</h2>
        {connected ? (
          <p>Chess.com account connected.</p>
        ) : (
          <label>
            Chess.com username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username"
            />
          </label>
        )}
        {!connected && (
          <button
            className="primary"
            onClick={async () => {
              setStatus("Connecting…");
              try {
                await api.post("/v1/integrations/chesscom", { username });
                onConnected();
                setStatus("Connected successfully.");
              } catch (e: any) {
                setStatus(
                  e.response?.data?.detail || "Could not connect account.",
                );
              }
            }}
          >
            Connect account
          </button>
        )}
        {connected && (
          <button
            className="primary"
            onClick={async () => {
              try {
                const { data } = await api.post(
                  "/v1/integrations/chesscom/sync",
                  { sync_mode: "initial" },
                );
                setStatus(
                  `Sync started (${data.id}). Refresh the game list in a moment.`,
                );
              } catch (e: any) {
                setStatus(e.response?.data?.detail || "Could not start sync.");
              }
            }}
          >
            Import recent 3 months
          </button>
        )}
        {status && <p>{status}</p>}
      </div>
    </section>
  );
}
