import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { fetchEvents, fetchTally } from "../api";
import { ACTIVE_EVENT_ID, FALLBACK_EVENTS } from "../events";

function MetricCard({ label, value, icon, tone }) {
  return (
    <div className={`metric-card metric-card--${tone}`}>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <span className="metric-card__icon"><Icon name={icon} size={22} /></span>
    </div>
  );
}

export default function Tally() {
  const [events, setEvents] = useState(FALLBACK_EVENTS);
  const [selectedEventId, setSelectedEventId] = useState(ACTIVE_EVENT_ID);
  const [tally, setTally] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    fetchEvents()
      .then((result) => {
        if (!cancelled) {
          setEvents(result.events || []);
          setSelectedEventId(result.active_event_id || ACTIVE_EVENT_ID);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvents(FALLBACK_EVENTS);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadTally() {
      setLoading(true);
      setError("");

      try {
        const result = await fetchTally(selectedEventId);
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
  }, [reloadKey, selectedEventId]);

  const yesPercent = tally?.total ? Math.round((tally.yes / tally.total) * 100) : 0;
  const noPercent = tally?.total ? 100 - yesPercent : 0;
  const selectedEvent = events.find((event) => event.event_id === selectedEventId) || tally?.event;
  const statusDetail =
    tally?.status === "Completed"
      ? "Voting for this event has concluded and the published totals below are final."
      : tally?.status === "Coming Soon"
        ? "This event has not opened yet, so no ballots have been cast."
        : tally?.status === "Active"
          ? "Mock accreditation remains open for eligible voters."
          : `This demonstration event is ${String(tally?.status || "").toLowerCase()}.`;

  return (
    <section className="page">
      <div className="dashboard-heading">
        <div>
          <span className="section-kicker">Referendum reporting</span>
          <h1>Tally Dashboard</h1>
          <p>Aggregate counts loaded directly from the secure tally endpoint.</p>
        </div>
        <button className="button button--outline" type="button" onClick={() => setReloadKey((key) => key + 1)}>
          <Icon name="refresh" size={17} />
          Refresh Tally
        </button>
      </div>

      <div className="event-filter-bar">
        <div>
          <span className="section-kicker">Event results</span>
          <strong>{selectedEvent?.title || FALLBACK_EVENTS[0].title}</strong>
        </div>
        <label className="event-select">
          <span>Referendum event</span>
          <select value={selectedEventId} onChange={(event) => setSelectedEventId(event.target.value)}>
            {events.map((event) => (
              <option key={event.event_id} value={event.event_id}>
                {event.title}{event.status ? ` - ${event.status}` : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <div className="dashboard-loading"><span className="spinner" /><strong>Loading referendum tally...</strong></div>
      ) : null}
      {error ? (
        <div className="connection-error">
          <span><Icon name="refresh" size={22} /></span>
          <div><strong>Unable to connect to the tally service</strong><p>{error}</p></div>
        </div>
      ) : null}
      {!loading && !error && tally ? (
        <>
          <div className="metric-grid">
            <MetricCard label="Total Registered Voters" value={tally.total_registered_voters} icon="user" tone="navy" />
            <MetricCard label="Event Ballots Cast" value={tally.total_ballots_cast} icon="ballot" tone="mint" />
            <MetricCard label="Remaining Voters" value={tally.remaining_voters} icon="clock" tone="gold" />
            <div className="metric-card metric-card--status">
              <div>
                <span>Event Status</span>
                <strong>{tally.status}</strong>
                <small>{statusDetail}</small>
              </div>
              <span className="metric-card__icon"><Icon name="clock" size={22} /></span>
            </div>
          </div>

          <div className="tally-grid">
            <div className="result-card">
              <div className="result-card__header">
                <div><span className="section-kicker">Current result</span><h2>{selectedEvent?.title}</h2></div>
                <span className="status-badge status-badge--neutral">Aggregate only</span>
              </div>
              <div className="result-bars">
                <div>
                  <p><strong>Yes</strong><span>{tally.yes} ballots | {yesPercent}%</span></p>
                  <div className="result-bar"><i style={{ width: `${yesPercent}%` }} /></div>
                </div>
                <div>
                  <p><strong>No</strong><span>{tally.no} ballots | {noPercent}%</span></p>
                  <div className="result-bar result-bar--no"><i style={{ width: `${noPercent}%` }} /></div>
                </div>
              </div>
              {tally.total === 0 ? <p className="result-card__empty">No ballots have been counted yet.</p> : null}
            </div>

            <div className="integrity-card">
              <span className="integrity-card__icon"><Icon name="shield" size={30} /></span>
              <span className="section-kicker section-kicker--light">Tally integrity</span>
              <h2>Publicly auditable.<br />Voter-private.</h2>
              <p>
                Counts and election status are returned by the existing tally service.
                Individual ballot choices are not exposed on the public verification board.
              </p>
              <div><Icon name="check" size={17} /> Public proof receipts</div>
              <div><Icon name="check" size={17} /> No voter identity shown</div>
              <div><Icon name="check" size={17} /> No raw vote published</div>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
