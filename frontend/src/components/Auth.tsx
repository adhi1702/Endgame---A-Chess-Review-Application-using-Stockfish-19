import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Activity, ArrowRight, ShieldCheck } from "lucide-react";
import { api } from "../api";

export function Auth({ onAuth, message }: { onAuth: () => void; message: string }) {
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
  async function startLink(e: FormEvent) {
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
