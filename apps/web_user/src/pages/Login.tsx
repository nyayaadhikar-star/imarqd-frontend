// apps/web/src/pages/Login.tsx
import { useState } from "react";
import { apiLogin /* , apiUploadPublicKey */ } from "../lib/api";
import { generateKeypair, savePGP, loadPGP } from "../lib/pgp";
import { normalizeEmail, sha256Hex } from "../lib/crypto";
import { saveAuth } from "../lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setStatus("Signing in…");

    try {
      // 1) Login
      const norm = normalizeEmail(email);
      const resp = await apiLogin(norm, password); // { token, uuid, email }
      const email_sha = await sha256Hex(norm);

      // 2) Save session
      saveAuth({ token: resp.token, uuid: resp.uuid, email: norm, email_sha });

      // 3) Ensure a local PGP keypair (upload later if you want)
      let pgp = loadPGP();
      if (!pgp) {
        setStatus("Generating secure keys (first time) …");
        const keys = await generateKeypair(norm, norm.split("@")[0]);
        savePGP(keys.publicKeyArmored, keys.privateKeyArmored);
        pgp = { pub: keys.publicKeyArmored, priv: keys.privateKeyArmored };
      }

      // Optional: upload public key to server for backup/association
      // setStatus("Uploading public key …");
      // await apiUploadPublicKey(resp.uuid, pgp.pub, resp.token);

      setStatus("All set! Redirecting …");
      setTimeout(() => (window.location.hash = "#/watermark"), 500);
    } catch (err: any) {
      setStatus(err?.response?.data?.detail || err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-bg">
      <div className="auth-center">
        <div className="card">
          <div className="card-head">
            <div className="brand-dot" />
            <h2 className="card-title">Welcome back</h2>
            <p className="card-sub">Sign in to protect & verify your media.</p>
          </div>

          <form onSubmit={onSubmit} className="form">
            <label className="label">Email</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@example.com"
              required
            />

            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              required
            />

            <button className={`btn ${busy ? "btn-disabled" : ""}`} type="submit" disabled={busy}>
              {busy ? (
                <>
                  <span className="spinner" /> Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {status && (
            <div className="status">
              {status}
            </div>
          )}

          <div className="foot-note">
            New here? Just sign in with any email — we create your account automatically.
          </div>
        </div>
      </div>
    </div>
  );
}
