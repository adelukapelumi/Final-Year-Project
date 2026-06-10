import { Link } from "react-router-dom";
import Icon from "../components/Icon";

const safeguards = [
  {
    icon: "user",
    title: "Accredit",
    text: "Confirm eligibility with an 11-digit mock NIN and a camera-based face-presence check."
  },
  {
    icon: "ballot",
    title: "Vote",
    text: "Cast one private Yes or No ballot in the active diaspora referendum."
  },
  {
    icon: "shield",
    title: "Verify",
    text: "Use public proof metadata to verify inclusion without revealing identity or choice."
  }
];

export default function Home() {
  return (
    <section className="page landing-page template-landing">
      <div className="landing-hero">
        <div className="landing-hero__content">
          <div className="eyebrow">
            <span className="eyebrow__dot" />
            Secure civic participation abroad
          </div>
          <h1>One referendum.<br />Every eligible voice.</h1>
          <p>
            DiasporaVote is a secure binary referendum portal for eligible Nigerians abroad.
            Complete prototype accreditation, vote privately, and verify the public proof receipt.
          </p>
          <div className="actions">
            <Link className="button button--primary" to="/login">
              Start Accreditation
              <Icon name="arrow" size={18} />
            </Link>
            <Link className="button button--outline" to="/board">
              View Public Board
            </Link>
          </div>
          <div className="trust-row">
            <span><Icon name="shield" size={17} /> Zero-knowledge proof receipts</span>
            <span><Icon name="globe" size={17} /> Built for Nigerians abroad</span>
          </div>
        </div>

        <div className="vote-illustration" aria-label="Illustration of secure online referendum voting">
          <span className="vote-illustration__halo" />
          <div className="vote-device">
            <div className="vote-device__speaker" />
            <div className="vote-device__screen">
              <span className="status-badge status-badge--success">Active</span>
              <Icon name="ballot" size={40} />
              <strong>REFERENDUM</strong>
              <div><span>YES</span><span>NO</span></div>
            </div>
            <span className="vote-device__button" />
          </div>
          <div className="illustration-person illustration-person--left">
            <span className="person-head" />
            <span className="person-body" />
            <span className="person-arm" />
          </div>
          <div className="illustration-person illustration-person--right">
            <span className="person-head" />
            <span className="person-body" />
            <span className="person-arm" />
          </div>
          <span className="illustration-check"><Icon name="check" size={24} /></span>
        </div>
      </div>

      <div className="landing-intro">
        <div>
          <span className="section-kicker">Simple, secure, auditable</span>
          <h2>A clear path from accreditation to public verification.</h2>
        </div>
        <p>
          The prototype keeps voter identity, session credentials, and ballot choice away from
          the public board while preserving a verifiable proof receipt.
        </p>
      </div>

      <div className="safeguard-grid">
        {safeguards.map((item, index) => (
          <article className="safeguard-card" key={item.title}>
            <span className="safeguard-card__index">0{index + 1}</span>
            <span className="icon-tile"><Icon name={item.icon} /></span>
            <h2>{item.title}</h2>
            <p>{item.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
