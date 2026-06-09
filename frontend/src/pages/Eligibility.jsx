import Icon from "../components/Icon";

export default function Eligibility({ session, onConfirmed }) {
  return (
    <section className="page narrow-page">
      <div className="step-heading">
        <div>
          <span className="section-kicker">Step 2 of 6</span>
          <h1>Eligibility Confirmation</h1>
          <p>Your mock NIN accreditation was successful. Review the eligibility statement before continuing.</p>
        </div>
        <span className="secure-chip"><Icon name="lock" size={15} /> Secure session</span>
      </div>

      <div className="eligibility-card">
        <div className="eligibility-card__seal">
          <span><Icon name="check" size={34} /></span>
        </div>
        <div className="eligibility-card__body">
          <span className="status-badge status-badge--success">Accreditation confirmed</span>
          <h2>You are eligible to participate</h2>
          <p>
            Your credential matched an eligible prototype voter record. No personal
            identity data will be attached to the public ballot receipt, and ballot access
            will open only after BVAS-inspired prototype verification.
          </p>

          <div className="confirmation-list">
            <div><Icon name="check" size={18} /><span>Identity credential accepted</span></div>
            <div><Icon name="check" size={18} /><span>Voting eligibility confirmed</span></div>
            <div><Icon name="check" size={18} /><span>BVAS-inspired prototype verification pending</span></div>
          </div>

          <div className="privacy-note">
            <Icon name="shield" size={22} />
            <div>
              <strong>Privacy notice</strong>
              <span>
                {session?.fallbackMessage ||
                  "This prototype simulates biometric accreditation and does not connect to live INEC or NIMC systems."}
              </span>
            </div>
          </div>

          <button className="button button--primary button--wide" type="button" onClick={onConfirmed}>
            Continue to Prototype Face Verification
            <Icon name="arrow" size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
