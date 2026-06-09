import { useState } from "react";
import Icon from "../components/Icon";
import { authenticate } from "../api";

export default function Login({ session, onAuthenticated }) {
  const [nin, setNin] = useState("");
  const [busyMode, setBusyMode] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(mode) {
    setBusyMode(mode);
    setError("");

    try {
      const result = await authenticate(nin, mode);
      onAuthenticated({
        token: result.token,
        ninHash: result.nin_hash
      });
    } catch (requestError) {
      setError(requestError.message || "Accreditation failed.");
    } finally {
      setBusyMode("");
    }
  }

  return (
    <section className="page auth-page">
      <div className="auth-panel auth-panel--intro">
        <div>
          <span className="section-kicker section-kicker--light">Voter access</span>
          <h1>Accreditation that protects your identity.</h1>
          <p>
            Confirm your eligibility through the existing secure voter endpoint.
            Your identity credential is never published with your ballot.
          </p>
        </div>

        <div className="auth-assurances">
          <div>
            <span><Icon name="shield" /></span>
            <p><strong>Private session</strong>Your credential remains separate from your vote.</p>
          </div>
          <div>
            <span><Icon name="lock" /></span>
            <p><strong>Encrypted ballot</strong>Your selection is protected before publication.</p>
          </div>
          <div>
            <span><Icon name="receipt" /></span>
            <p><strong>Verifiable receipt</strong>Receive public proof metadata after submission.</p>
          </div>
        </div>

        <div className="auth-panel__foot">
          <Icon name="globe" size={18} />
          Designed for eligible Nigerians abroad
        </div>
      </div>

      <div className="auth-panel auth-panel--form">
        <div className="auth-form">
          <span className="section-kicker">Step 1 of 5</span>
          <h2>Voter Accreditation</h2>
          <p className="muted">
            Enter your prototype National Identification Number to begin.
          </p>

          <div className="field">
            <label htmlFor="nin">National Identification Number</label>
            <div className="input-wrap">
              <Icon name="user" size={19} />
              <input
                autoComplete="off"
                id="nin"
                inputMode="numeric"
                maxLength={11}
                placeholder="Enter 11-digit mock NIN"
                value={nin}
                onChange={(event) => setNin(event.target.value.replace(/\D/g, ""))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !busyMode) {
                    handleSubmit("login");
                  }
                }}
              />
            </div>
            <small>Prototype credential only. Use a configured development NIN.</small>
          </div>

          {error ? (
            <div className="status status--error">
              <strong>Connection or accreditation error</strong>
              <span>{error}</span>
            </div>
          ) : null}

          <button
            type="button"
            className="button button--primary button--wide"
            disabled={Boolean(busyMode) || nin.length !== 11}
            onClick={() => handleSubmit("login")}
          >
            {busyMode === "login" ? "Confirming eligibility..." : "Accredit & Continue"}
            {!busyMode ? <Icon name="arrow" size={18} /> : <span className="spinner spinner--small" />}
          </button>

          <div className="register-divider"><span>First time in this prototype?</span></div>

          <button
            type="button"
            className="button button--outline button--wide"
            disabled={Boolean(busyMode) || nin.length !== 11}
            onClick={() => handleSubmit("register")}
          >
            {busyMode === "register" ? "Registering..." : "Register Prototype Voter"}
          </button>

          {session?.token ? (
            <div className="status status--success">
              <Icon name="check" size={18} />
              <span>An authenticated session is already available.</span>
            </div>
          ) : null}

          <p className="form-security"><Icon name="lock" size={14} /> Secured session transport</p>
        </div>
      </div>
    </section>
  );
}
