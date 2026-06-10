import { useState } from "react";
import { Link } from "react-router-dom";
import Icon from "../components/Icon";

function ReceiptRow({ label, value, code, onCopy }) {
  return (
    <div className="receipt-row">
      <span>{label}</span>
      <div>
        {code ? <code>{value}</code> : <strong>{value}</strong>}
        {onCopy ? (
          <button aria-label={`Copy ${label}`} className="copy-button" type="button" onClick={onCopy}>
            <Icon name="copy" size={17} />
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function Receipt({ receipt }) {
  const [copied, setCopied] = useState("");

  async function copyValue(label, value) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      window.setTimeout(() => setCopied(""), 1600);
    } catch {
      setCopied("");
    }
  }

  if (!receipt) {
    return (
      <section className="page narrow-page">
        <div className="empty-state">
          <span className="icon-tile"><Icon name="receipt" size={26} /></span>
          <h1>No vote receipt yet</h1>
          <p>Complete the referendum ballot to generate a public proof receipt.</p>
          <Link className="button button--primary" to="/ballot">Go to Referendum Ballot</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="page narrow-page">
      <div className="receipt-success">
        <span className="receipt-success__icon"><Icon name="check" size={34} /></span>
        <span className="section-kicker">Step 6 of 6 · Submission complete</span>
        <h1>Your vote has been securely recorded.</h1>
        <p>Keep this receipt to locate and verify your ballot proof on the public board.</p>
      </div>

      <div className="receipt-card">
        <div className="receipt-card__header">
          <div>
            <span className="receipt-card__eyebrow">DiasporaVote</span>
            <h2>Cryptographic Vote Receipt</h2>
          </div>
          <span className={`status-badge ${receipt.verified ? "status-badge--success" : "status-badge--error"}`}>
            <Icon name={receipt.verified ? "check" : "clock"} size={14} />
            {receipt.verified ? "Proof verified" : "Verification unavailable"}
          </span>
        </div>

        <div className="receipt-data">
          <ReceiptRow label="Referendum event" value={receipt.eventTitle} />
          <ReceiptRow code label="Event ID" value={receipt.eventId} />
          <ReceiptRow
            code
            label="Ballot ID"
            value={receipt.ballotId}
            onCopy={() => copyValue("Ballot ID", receipt.ballotId)}
          />
          <ReceiptRow
            code
            label="Proof hash"
            value={receipt.proofHash}
            onCopy={() => copyValue("Proof hash", receipt.proofHash)}
          />
          <ReceiptRow label="Timestamp" value={receipt.timestamp} />
          <ReceiptRow label="Verification status" value={receipt.verified ? "Verified" : "Unavailable"} />
        </div>

        {copied ? <div className="copy-toast">{copied} copied</div> : null}

        <div className="receipt-card__notice">
          <Icon name="lock" size={18} />
          This receipt does not reveal your identity or ballot choice.
        </div>
      </div>

      <div className="receipt-actions">
        <Link className="button button--primary" to="/board">
          Find on Public Board
          <Icon name="arrow" size={18} />
        </Link>
        <Link className="button button--outline" to="/tally">View Tally Dashboard</Link>
      </div>
    </section>
  );
}
