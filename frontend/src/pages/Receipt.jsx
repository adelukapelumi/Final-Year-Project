import { Link } from "react-router-dom";

export default function Receipt({ receipt }) {
  if (!receipt) {
    return (
      <section className="page">
        <div className="card stack">
          <h2>No receipt yet</h2>
          <p className="muted">
            Submit a ballot first to generate a receipt with the public proof details.
          </p>
          <div className="actions">
            <Link className="button" to="/ballot">
              Go to Ballot
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="hero">
        <h2>Voting Receipt</h2>
        <p className="muted">
          Only public ballot metadata is shown here. Sensitive voter details stay hidden.
        </p>
      </div>

      <div className="card data-grid">
        <div className="data-row">
          <strong>Ballot ID</strong>
          <code>{receipt.ballotId}</code>
        </div>
        <div className="data-row">
          <strong>Proof Hash</strong>
          <code>{receipt.proofHash}</code>
        </div>
        <div className="data-row">
          <strong>Timestamp</strong>
          <span>{receipt.timestamp}</span>
        </div>
      </div>
    </section>
  );
}
