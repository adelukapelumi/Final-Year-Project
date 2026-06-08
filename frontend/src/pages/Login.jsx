import { useState } from "react";
import { authenticate } from "../api";

export default function Login({ session, onAuthenticated }) {
  const [nin, setNin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(mode) {
    setBusy(true);
    setError("");
    setSuccess("");

    try {
      const result = await authenticate(nin, mode);
      onAuthenticated({
        token: result.token,
        ninHash: result.nin_hash
      });
      setSuccess(`${mode === "register" ? "Registration" : "Login"} successful.`);
    } catch (requestError) {
      setError(requestError.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <div className="hero">
        <h2>Voter Login</h2>
        <p className="muted">
          Enter a mock National Identification Number to access the referendum ballot.
        </p>
      </div>

      <div className="card stack">
        <div className="field">
          <label htmlFor="nin">Mock NIN</label>
          <input
            id="nin"
            inputMode="numeric"
            maxLength={11}
            placeholder="12345678901"
            value={nin}
            onChange={(event) => setNin(event.target.value)}
          />
        </div>

        <div className="actions">
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={() => handleSubmit("login")}
          >
            {busy ? "Working..." : "Login"}
          </button>
          <button
            type="button"
            className="button button--secondary"
            disabled={busy}
            onClick={() => handleSubmit("register")}
          >
            {busy ? "Working..." : "Register"}
          </button>
        </div>

        {error ? <div className="status status--error">{error}</div> : null}
        {success ? <div className="status status--success">{success}</div> : null}

        <div className="data-row">
          <strong>Session</strong>
          <span>{session?.token ? "Authenticated and ready to vote." : "No active session yet."}</span>
        </div>
      </div>
    </section>
  );
}
