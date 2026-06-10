import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { fetchBoard, verifyBallot } from "../api";

function formatVerificationTimestamp(value) {
  if (!value) {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "medium"
    }).format(new Date());
  }

  return value;
}

function buildVerificationResult({
  ballotId,
  proofHash,
  boardProofHash,
  verified,
  timestamp,
  error = ""
}) {
  const hashMatches = Boolean(boardProofHash) && proofHash === boardProofHash;
  const success = Boolean(verified) && hashMatches && !error;

  return {
    ballotId,
    proofHash: proofHash || "Unavailable",
    boardProofHash: boardProofHash || "Unavailable on public board",
    verified: Boolean(verified) && !error,
    hashMatches,
    success,
    timestamp: formatVerificationTimestamp(timestamp),
    error,
    message: success
      ? "Proof verified and receipt hash matches public board record."
      : "Proof verification failed or receipt mismatch."
  };
}

export default function PublicBoard() {
  const [ballots, setBallots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [receiptQuery, setReceiptQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [verifyingBallotId, setVerifyingBallotId] = useState("");
  const [verificationResult, setVerificationResult] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadBoard() {
      setLoading(true);
      setError("");

      try {
        const result = await fetchBoard();
        if (!cancelled) {
          setBallots(result.ballots || []);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message || "Could not load the public board.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadBoard();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const normalizedQuery = query.trim().toLowerCase();
  const visibleBallots = normalizedQuery
    ? ballots.filter((ballot) => ballot.ballot_id.toLowerCase().includes(normalizedQuery))
    : ballots;
  const normalizedReceiptQuery = receiptQuery.trim();

  async function runVerification(ballotId, boardProofHash = "") {
    const normalizedBallotId = String(ballotId || "").trim();
    const boardBallot = ballots.find((ballot) => ballot.ballot_id === normalizedBallotId);
    const publicProofHash = boardProofHash || boardBallot?.proof_hash || "";

    if (!normalizedBallotId) {
      setVerificationResult(
        buildVerificationResult({
          ballotId: "Unavailable",
          proofHash: "",
          boardProofHash: publicProofHash,
          verified: false,
          timestamp: "",
          error: "Enter a Ballot ID before attempting verification."
        })
      );
      return;
    }

    setReceiptQuery(normalizedBallotId);
    setVerifyingBallotId(normalizedBallotId);

    try {
      const result = await verifyBallot(normalizedBallotId);
      setVerificationResult(
        buildVerificationResult({
          ballotId: result.ballot_id || normalizedBallotId,
          proofHash: result.proof_hash || "",
          boardProofHash: publicProofHash,
          verified: result.verified,
          timestamp: result.timestamp || ""
        })
      );
    } catch (requestError) {
      setVerificationResult(
        buildVerificationResult({
          ballotId: normalizedBallotId,
          proofHash: "",
          boardProofHash: publicProofHash,
          verified: false,
          timestamp: "",
          error: requestError.message || "Verification request failed."
        })
      );
    } finally {
      setVerifyingBallotId("");
    }
  }

  function handleReceiptVerification(event) {
    event.preventDefault();
    runVerification(normalizedReceiptQuery);
  }

  return (
    <section className="page">
      <div className="dashboard-heading">
        <div>
          <span className="section-kicker">Public audit record</span>
          <h1>Public Verification Board</h1>
          <p>Review published proof receipts without exposing voter identity or ballot choice.</p>
        </div>
        <button className="button button--outline" type="button" onClick={() => setReloadKey((key) => key + 1)}>
          <Icon name="refresh" size={17} />
          Refresh Board
        </button>
      </div>

      <div className="board-summary">
        <div>
          <span className="icon-tile"><Icon name="board" /></span>
          <p><small>Published receipts</small><strong>{loading ? "-" : ballots.length}</strong></p>
        </div>
        <div className="board-summary__privacy">
          <Icon name="shield" size={22} />
          <p><strong>Privacy-preserving record</strong><span>Only public cryptographic metadata is displayed.</span></p>
        </div>
      </div>

      <div className="verification-card">
        <div className="verification-card__header">
          <div>
            <span className="section-kicker">Server-mediated verification</span>
            <h2>Verify a public ballot receipt</h2>
            <p>Paste a Ballot ID or use any board row to re-run proof verification without revealing identity or ballot choice.</p>
          </div>
        </div>

        <form className="verification-form" onSubmit={handleReceiptVerification}>
          <label className="input-wrap verification-form__input">
            <Icon name="receipt" size={18} />
            <input
              aria-label="Verify receipt by ballot ID"
              placeholder="Paste Ballot ID from receipt"
              value={receiptQuery}
              onChange={(event) => setReceiptQuery(event.target.value)}
            />
          </label>
          <button
            className="button button--primary"
            type="submit"
            disabled={!normalizedReceiptQuery || Boolean(verifyingBallotId)}
          >
            <Icon name={verifyingBallotId === normalizedReceiptQuery ? "clock" : "shield"} size={17} />
            {verifyingBallotId === normalizedReceiptQuery ? "Verifying..." : "Verify Receipt"}
          </button>
        </form>

        {verificationResult ? (
          <div className="verification-result">
            <div className="verification-result__summary">
              <span className={`status-badge ${verificationResult.success ? "status-badge--success" : "status-badge--error"}`}>
                <Icon name={verificationResult.success ? "check" : "close"} size={14} />
                {verificationResult.success ? "Proof verified" : "Verification failed"}
              </span>
              <p>{verificationResult.message}</p>
            </div>

            <div className="verification-result__grid">
              <div>
                <small>Ballot ID</small>
                <code>{verificationResult.ballotId}</code>
              </div>
              <div>
                <small>Proof hash</small>
                <code>{verificationResult.proofHash}</code>
              </div>
              <div>
                <small>Public board hash</small>
                <code>{verificationResult.boardProofHash}</code>
              </div>
              <div>
                <small>Verification timestamp</small>
                <strong>{verificationResult.timestamp}</strong>
              </div>
            </div>

            {verificationResult.error ? (
              <div className="status status--error">
                <div>
                  <strong>Verification detail</strong>
                  <span>{verificationResult.error}</span>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="verification-card__hint">
            <Icon name="shield" size={18} />
            <span>Use a board row or paste a Ballot ID to confirm the public receipt hash against the verifier response.</span>
          </div>
        )}
      </div>

      <div className="table-card">
        <div className="table-toolbar">
          <div>
            <h2>Published Ballots</h2>
            <span>{loading ? "Connecting to public board..." : `${visibleBallots.length} record${visibleBallots.length === 1 ? "" : "s"} shown`}</span>
          </div>
          <label className="search-field">
            <Icon name="board" size={17} />
            <input
              aria-label="Search by ballot ID"
              placeholder="Search ballot ID"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>

        {loading ? (
          <div className="loading-state"><span className="spinner" /><strong>Loading public verification records...</strong></div>
        ) : null}
        {error ? (
          <div className="connection-error">
            <span><Icon name="refresh" size={22} /></span>
            <div><strong>Unable to connect to the public board</strong><p>{error}</p></div>
          </div>
        ) : null}
        {!loading && !error && ballots.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <span className="icon-tile"><Icon name="board" /></span>
            <h2>No ballots published yet</h2>
            <p>Proof receipts will appear here after successful submissions.</p>
          </div>
        ) : null}
        {!loading && !error && ballots.length > 0 ? (
          <>
            <div className="board-table">
              <div className="board-table__head">
                <span>Ballot ID</span>
                <span>Proof Hash</span>
                <span>Timestamp</span>
                <span>Verification result</span>
              </div>
              {visibleBallots.map((ballot) => (
                <div className="board-table__row" key={ballot.ballot_id}>
                  <div data-label="Ballot ID"><code>{ballot.ballot_id}</code></div>
                  <div data-label="Proof Hash"><code>{ballot.proof_hash}</code></div>
                  <div data-label="Timestamp"><span>{ballot.timestamp}</span></div>
                  <div data-label="Verification result" className="board-table__actions">
                    <button
                      className="button button--outline button--small"
                      type="button"
                      disabled={Boolean(verifyingBallotId)}
                      onClick={() => runVerification(ballot.ballot_id, ballot.proof_hash)}
                    >
                      <Icon name={verifyingBallotId === ballot.ballot_id ? "clock" : "shield"} size={15} />
                      {verifyingBallotId === ballot.ballot_id
                        ? "Verifying..."
                        : verificationResult?.ballotId === ballot.ballot_id && verificationResult.success
                          ? "Verified"
                          : "Verify Proof"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {visibleBallots.length === 0 ? (
              <div className="empty-state empty-state--compact">
                <h2>No matching ballot ID</h2>
                <p>Check the receipt identifier and try again.</p>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
