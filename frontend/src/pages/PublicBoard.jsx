import { useEffect, useState } from "react";
import { fetchBoard } from "../api";

export default function PublicBoard() {
  const [ballots, setBallots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
  }, []);

  return (
    <section className="page">
      <div className="hero">
        <h2>Public Board</h2>
        <p className="muted">
          This board lists public proof records only: ballot ID, proof hash, and timestamp.
        </p>
      </div>

      <div className="card stack">
        {loading ? <div className="status">Loading board...</div> : null}
        {error ? <div className="status status--error">{error}</div> : null}
        {!loading && !error && ballots.length === 0 ? (
          <div className="status">No ballots have been published yet.</div>
        ) : null}
        {!loading && !error && ballots.length > 0 ? (
          <div className="data-grid">
            {ballots.map((ballot) => (
              <div className="data-row" key={ballot.ballot_id}>
                <strong>Ballot ID</strong>
                <code>{ballot.ballot_id}</code>
                <strong>Proof Hash</strong>
                <code>{ballot.proof_hash}</code>
                <strong>Timestamp</strong>
                <span>{ballot.timestamp}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
