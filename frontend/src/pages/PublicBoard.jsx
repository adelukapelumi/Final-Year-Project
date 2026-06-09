import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { fetchBoard } from "../api";

export default function PublicBoard() {
  const [ballots, setBallots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

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
          <p><small>Published receipts</small><strong>{loading ? "—" : ballots.length}</strong></p>
        </div>
        <div className="board-summary__privacy">
          <Icon name="shield" size={22} />
          <p><strong>Privacy-preserving record</strong><span>Only public cryptographic metadata is displayed.</span></p>
        </div>
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
              </div>
              {visibleBallots.map((ballot) => (
                <div className="board-table__row" key={ballot.ballot_id}>
                  <div data-label="Ballot ID"><code>{ballot.ballot_id}</code></div>
                  <div data-label="Proof Hash"><code>{ballot.proof_hash}</code></div>
                  <div data-label="Timestamp"><span>{ballot.timestamp}</span></div>
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
