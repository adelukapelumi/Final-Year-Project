import { useState } from "react";
import Icon from "../components/Icon";
import { runBiometricVerification } from "../api";

export default function BiometricVerification({ session, onVerified }) {
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedProbeId, setSelectedProbeId] = useState(
    session?.biometric?.recommendedProbeId || session?.biometric?.availableProbes?.[0]?.id || ""
  );

  const availableProbes = session?.biometric?.availableProbes || [];
  const fallbackMessage =
    session?.fallbackMessage ||
    session?.biometric?.fallbackMessage ||
    "This prototype simulates biometric accreditation and does not connect to live INEC or NIMC systems.";

  async function handleVerification() {
    setIsBusy(true);
    setError("");

    try {
      await runBiometricVerification(session.token, selectedProbeId);
      onVerified();
    } catch (requestError) {
      setError(requestError.message || "Mock facial verification failed.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="page narrow-page">
      <div className="step-heading">
        <div>
          <span className="section-kicker">Step 3 of 6</span>
          <h1>BVAS-inspired Prototype Verification</h1>
          <p>Run a mock facial verification step before the referendum ballot is unlocked.</p>
        </div>
        <span className="secure-chip"><Icon name="shield" size={15} /> Prototype biometric gate</span>
      </div>

      <div className="eligibility-card">
        <div className="eligibility-card__seal">
          <span><Icon name="shield" size={34} /></span>
        </div>
        <div className="eligibility-card__body">
          <span className="status-badge status-badge--neutral">BVAS-inspired prototype verification</span>
          <h2>Mock facial verification required before ballot access</h2>
          <p>
            Your mock NIN has been accredited. Complete the prototype facial-verification step
            to simulate biometric accreditation before ballot access is granted.
          </p>

          <div className="confirmation-list">
            <div><Icon name="check" size={18} /><span>Mock eligible registry matched</span></div>
            <div><Icon name="check" size={18} /><span>No live INEC or NIMC integration</span></div>
            <div><Icon name="check" size={18} /><span>Binary referendum ballot remains unchanged</span></div>
          </div>

          <div className="field">
            <label htmlFor="probeId">Preloaded development face sample</label>
            <div className="input-wrap">
              <Icon name="user" size={19} />
              <select
                id="probeId"
                value={selectedProbeId}
                onChange={(event) => setSelectedProbeId(event.target.value)}
              >
                {availableProbes.map((probe) => (
                  <option key={probe.id} value={probe.id}>
                    {probe.label}
                  </option>
                ))}
              </select>
            </div>
            <small>{session?.biometric?.developmentProfileLabel || "Prototype mock face sample is preloaded for development."}</small>
          </div>

          <div className="privacy-note">
            <Icon name="shield" size={22} />
            <div>
              <strong>Prototype-only accreditation</strong>
              <span>{fallbackMessage}</span>
            </div>
          </div>

          {error ? (
            <div className="status status--error">
              <strong>Verification error</strong>
              <span>{error}</span>
            </div>
          ) : null}

          <button className="button button--primary button--wide" type="button" onClick={handleVerification} disabled={isBusy || !selectedProbeId}>
            {isBusy ? "Running Prototype Face Match..." : "Run Prototype Face Match"}
            {!isBusy ? <Icon name="arrow" size={18} /> : <span className="spinner spinner--small" />}
          </button>
        </div>
      </div>
    </section>
  );
}
