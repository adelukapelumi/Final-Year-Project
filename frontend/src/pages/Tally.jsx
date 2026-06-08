import { useEffect, useState } from "react";
import { fetchTally } from "../api";

export default function Tally() {
  const [tally, setTally] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadTally() {
      setLoading(true);
      setError("");

      try {
        const result = await fetchTally();
        if (!cancelled) {
          setTally(result);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message || "Could not load the tally.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTally();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="page">
      <div className="hero">
        <h2>Referendum Tally</h2>
        <p className="muted">Live counts are loaded from the Flask backend tally endpoint.</p>
      </div>

      <div className="card stack">
        {loading ? <div className="status">Loading tally...</div> : null}
        {error ? <div className="status status--error">{error}</div> : null}
        {!loading && !error && tally ? (
          <div className="metrics">
            <div className="metric">
              <strong>Yes</strong>
              <span>{tally.yes}</span>
            </div>
            <div className="metric">
              <strong>No</strong>
              <span>{tally.no}</span>
            </div>
            <div className="metric">
              <strong>Total</strong>
              <span>{tally.total}</span>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
