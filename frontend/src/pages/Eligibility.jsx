import Icon from "../components/Icon";

export default function Eligibility({ onConfirmed }) {
  return (
    <section className="page narrow-page">
      <div className="step-heading">
        <div>
          <span className="section-kicker">Step 2 of 5</span>
          <h1>Eligibility Confirmation</h1>
          <p>Your accreditation was successful. Review the eligibility statement before continuing.</p>
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
            identity data will be attached to the public ballot receipt.
          </p>

          <div className="confirmation-list">
            <div><Icon name="check" size={18} /><span>Identity credential accepted</span></div>
            <div><Icon name="check" size={18} /><span>Voting eligibility confirmed</span></div>
            <div><Icon name="check" size={18} /><span>Private ballot session established</span></div>
          </div>

          <div className="privacy-note">
            <Icon name="shield" size={22} />
            <div>
              <strong>Privacy notice</strong>
              <span>Your NIN and session credential will never appear on the public board.</span>
            </div>
          </div>

          <button className="button button--primary button--wide" type="button" onClick={onConfirmed}>
            Continue to Referendum Ballot
            <Icon name="arrow" size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
