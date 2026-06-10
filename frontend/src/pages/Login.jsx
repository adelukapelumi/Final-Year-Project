import { useState } from "react";
import Icon from "../components/Icon";
import { authenticate } from "../api";

export default function Login({ onAuthenticated }) {
  const [nin, setNin] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event?.preventDefault();
    setIsBusy(true);
    setError("");

    try {
      const result = await authenticate(nin, "login");
      onAuthenticated({
        token: result.token,
        profile: {
          displayName: result.profile?.display_name,
          diasporaLocation: result.profile?.diaspora_location,
          voterCategory: result.profile?.voter_category
        },
        biometric: {
          verificationMode: result.biometric?.verification_mode,
          fallbackMessage: result.biometric?.fallback_message
        },
        fallbackMessage: result.fallback_message
      });
    } catch (requestError) {
      setError(requestError.message || "Accreditation failed.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="page auth-page accreditation-page">
      <div className="auth-panel auth-panel--intro">
        <div>
          <span className="section-kicker section-kicker--light">DiasporaVote accreditation</span>
          <h1>Your secure entry to the referendum.</h1>
          <p>
            Verify that your mock voter record is eligible, then complete camera-based
            prototype face verification before the ballot is unlocked.
          </p>
        </div>

        <div className="accreditation-steps">
          <div className="is-current"><span>01</span><p><strong>Verify eligibility</strong>11-digit mock NIN check</p></div>
          <div><span>02</span><p><strong>Scan face</strong>Camera presence verification</p></div>
          <div><span>03</span><p><strong>Open dashboard</strong>Review the active event</p></div>
        </div>

        <div className="auth-panel__foot">
          <Icon name="shield" size={18} />
          Identity details are never displayed on the public board
        </div>
      </div>

      <div className="auth-panel auth-panel--form">
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-form__mark"><Icon name="user" size={24} /></div>
          <span className="section-kicker">Step 1 of 3</span>
          <h2>Voter Accreditation</h2>
          <p className="muted">Enter your configured 11-digit mock NIN to verify eligibility.</p>

          <div className="field">
            <label htmlFor="nin">Mock National Identification Number</label>
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
              />
            </div>
            <small>Prototype credential only. No live NIMC or NIN API is used.</small>
          </div>

          <div className="privacy-note">
            <Icon name="shield" size={22} />
            <div>
              <strong>Private accreditation session</strong>
              <span>Your NIN and its hash are not shown in the voter dashboard or public records.</span>
            </div>
          </div>

          {error ? (
            <div className="status status--error">
              <strong>Accreditation error</strong>
              <span>{error}</span>
            </div>
          ) : null}

          <button
            type="submit"
            className="button button--primary button--wide"
            disabled={isBusy || nin.length !== 11}
          >
            {isBusy ? "Verifying Eligibility..." : "Verify Eligibility"}
            {!isBusy ? <Icon name="arrow" size={18} /> : <span className="spinner spinner--small" />}
          </button>

          <p className="form-security"><Icon name="lock" size={14} /> Encrypted session transport</p>
        </form>
      </div>
    </section>
  );
}
