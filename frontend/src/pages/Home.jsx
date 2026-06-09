import { Link } from "react-router-dom";
import Icon from "../components/Icon";

const safeguards = [
  {
    icon: "user",
    title: "Eligibility first",
    text: "Accreditation confirms access before a referendum ballot is shown."
  },
  {
    icon: "lock",
    title: "Private by design",
    text: "Your public receipt contains proof metadata, never your identity or vote."
  },
  {
    icon: "shield",
    title: "Cryptographic assurance",
    text: "Each submitted ballot is paired with a verifiable zk-STARK proof receipt."
  }
];

export default function Home() {
  return (
    <section className="page landing-page">
      <div className="landing-hero">
        <div className="landing-hero__content">
          <div className="eyebrow">
            <span className="eyebrow__dot" />
            Secure civic participation abroad
          </div>
          <h1>Your voice, verified.<br />Wherever you are.</h1>
          <p>
            Secure binary referendum portal for eligible Nigerians abroad.
            Accredit, cast your ballot, and verify its proof without exposing your choice.
          </p>
          <div className="actions">
            <Link className="button button--gold" to="/login">
              Begin Accreditation
              <Icon name="arrow" size={18} />
            </Link>
            <Link className="button button--light" to="/board">
              View Public Board
            </Link>
          </div>
          <div className="trust-row">
            <span><Icon name="shield" size={17} /> Zero-knowledge verified</span>
            <span><Icon name="globe" size={17} /> Built for the diaspora</span>
          </div>
        </div>

        <div className="referendum-preview" aria-label="Referendum overview">
          <div className="preview-orbit preview-orbit--one" />
          <div className="preview-orbit preview-orbit--two" />
          <div className="preview-card">
            <div className="preview-card__header">
              <span className="status-badge status-badge--neutral">Binary Referendum</span>
              <Icon name="shield" size={24} />
            </div>
            <div className="preview-card__number">01</div>
            <p>Should secure diaspora voting be enabled for eligible Nigerians abroad?</p>
            <div className="preview-card__options">
              <span><i /> Yes</span>
              <span><i /> No</span>
            </div>
            <div className="preview-card__footer">
              <Icon name="lock" size={16} />
              Ballot choices remain encrypted
            </div>
          </div>
        </div>
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
