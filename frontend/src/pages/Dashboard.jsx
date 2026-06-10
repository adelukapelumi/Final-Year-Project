import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { fetchEvents, fetchTally } from "../api";
import { ACTIVE_EVENT_ID, FALLBACK_EVENTS, getFallbackEvent } from "../events";

function EventAction({ event, onSelectEvent }) {
  if (event.action_enabled) {
    return (
      <button className="button button--primary" type="button" onClick={() => onSelectEvent(event)}>
        Proceed to Ballot
        <Icon name="arrow" size={18} />
      </button>
    );
  }

  return (
    <button className="button button--outline" type="button" disabled>
      {event.status === "Upcoming" ? "Coming Soon" : "Closed"}
    </button>
  );
}

function StatusBadge({ status }) {
  const tone = status === "Active" ? "success" : status === "Closed" ? "error" : "neutral";
  return <span className={`status-badge status-badge--${tone}`}>{status}</span>;
}

export default function Dashboard({ session, onEndSession, onSelectEvent }) {
  const [events, setEvents] = useState(FALLBACK_EVENTS);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadEvents() {
      try {
        const catalog = await fetchEvents();
        if (!active) {
          return;
        }
        const eventList = catalog.events?.length ? catalog.events : FALLBACK_EVENTS;
        setEvents(eventList);
        const currentEvent =
          eventList.find((event) => event.event_id === catalog.active_event_id) ||
          getFallbackEvent(catalog.active_event_id || ACTIVE_EVENT_ID);
        loadTally(currentEvent.event_id);
      } catch {
        if (active) {
          setEvents(FALLBACK_EVENTS);
          loadTally(ACTIVE_EVENT_ID);
        }
      }
    }

    async function loadTally(eventId) {
      try {
        const tally = await fetchTally(eventId);
        if (active) {
          setStats(tally);
          setStatsError("");
        }
      } catch (requestError) {
        if (active) {
          setStats(null);
          setStatsError(requestError.message || "Unable to load live event statistics.");
        }
      }
    }

    loadEvents();
    return () => {
      active = false;
    };
  }, []);

  const profile = session?.profile || {};
  const activeEvent = events.find((event) => event.status === "Active");
  const supportingEvents = events.filter((event) => event.event_id !== activeEvent?.event_id);
  const yesPercent = stats?.total ? Math.round((stats.yes / stats.total) * 100) : 0;
  const noPercent = stats?.total ? 100 - yesPercent : 0;

  return (
    <section className="page voter-dashboard">
      <div className="dashboard-welcome">
        <div>
          <span className="section-kicker">Authenticated voter portal</span>
          <h1>Welcome, {profile.displayName?.split(" ")[0] || "Voter"}.</h1>
          <p>Select an active referendum event before opening a ballot.</p>
        </div>
        <div className="dashboard-identity">
          {session?.capturedImage ? <img src={session.capturedImage} alt="Session profile" /> : null}
          <div>
            <strong>{profile.displayName || "Verified Voter"}</strong>
            <span><Icon name="map" size={14} /> {profile.diasporaLocation || "Diaspora"}</span>
          </div>
          <span className="status-badge status-badge--success"><Icon name="check" size={13} /> Verified</span>
          <button className="button button--outline button--small dashboard-end-session" type="button" onClick={onEndSession}>
            <Icon name="logout" size={15} />
            End Session
          </button>
        </div>
      </div>

      {statsError ? (
        <div className="connection-error">
          <span><Icon name="refresh" size={22} /></span>
          <div><strong>Unable to load live event statistics</strong><p>{statsError}</p></div>
        </div>
      ) : null}

      <div className="dashboard-stat-grid">
        <article>
          <span className="dashboard-stat__icon"><Icon name="user" /></span>
          <div><small>Prototype voters</small><strong>{stats?.total_registered_voters ?? "4"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--mint"><Icon name="ballot" /></span>
          <div><small>Active-event ballots</small><strong>{stats?.total_ballots_cast ?? "-"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--gold"><Icon name="clock" /></span>
          <div><small>Active event status</small><strong>{stats?.status || "Active"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--navy"><Icon name="board" /></span>
          <div><small>Referendum events</small><strong>{events.length}</strong></div>
        </article>
      </div>

      <div className="events-heading">
        <div>
          <span className="section-kicker">Referendum events</span>
          <h2>Select an election event</h2>
        </div>
        <p>Only active events with an enabled action can open a ballot.</p>
      </div>

      {activeEvent ? (
        <div className="dashboard-grid dashboard-grid--events">
          <article className="event-card">
            <div className="event-card__visual">
              <span className="event-card__ballot"><Icon name="ballot" size={38} /></span>
              <span className="event-card__ring" />
              <span className="event-card__ring event-card__ring--small" />
            </div>
            <div className="event-card__content">
              <div className="event-card__meta">
                <StatusBadge status={activeEvent.status} />
                <span>{activeEvent.ballot_type}</span>
              </div>
              <h2>{activeEvent.title}</h2>
              <p>{activeEvent.question}</p>
              <dl>
                <div><dt>Voting period</dt><dd>{activeEvent.start_date}</dd></div>
                <div><dt>Closes</dt><dd>{activeEvent.end_date}</dd></div>
                <div><dt>Eligibility</dt><dd><Icon name="check" size={14} /> Verified</dd></div>
              </dl>
              <EventAction event={activeEvent} onSelectEvent={onSelectEvent} />
            </div>
          </article>

          <aside className="live-event-card">
            <span className="section-kicker section-kicker--light">Live event snapshot</span>
            <h2>{activeEvent.title}</h2>
            <p>{stats?.total_ballots_cast ?? 0} ballots cast in this event.</p>
            <div className="mini-result">
              <div>
                <span><strong>Yes</strong><small>{stats?.yes ?? 0} · {yesPercent}%</small></span>
                <i><b style={{ width: `${yesPercent}%` }} /></i>
              </div>
              <div>
                <span><strong>No</strong><small>{stats?.no ?? 0} · {noPercent}%</small></span>
                <i><b style={{ width: `${noPercent}%` }} /></i>
              </div>
            </div>
            <div className="live-event-card__status">
              <Icon name="clock" size={17} />
              <span><strong>{stats?.status || "Active"}</strong> Reporting is scoped to this referendum.</span>
            </div>
          </aside>
        </div>
      ) : null}

      <div className="supporting-event-grid">
        {supportingEvents.map((event) => (
          <article className="supporting-event-card" key={event.event_id}>
            <div className="supporting-event-card__top">
              <span className="icon-tile"><Icon name={event.status === "Closed" ? "shield" : "clock"} /></span>
              <StatusBadge status={event.status} />
            </div>
            <span className="section-kicker">{event.ballot_type}</span>
            <h3>{event.title}</h3>
            <p>{event.description}</p>
            <div className="supporting-event-card__date">
              <Icon name="clock" size={15} />
              {event.start_date} · {event.end_date}
            </div>
            <EventAction event={event} onSelectEvent={onSelectEvent} />
          </article>
        ))}
      </div>

      <aside className="dashboard-side-card dashboard-session-card">
        <span className="icon-tile"><Icon name="shield" /></span>
        <div>
          <span className="section-kicker section-kicker--light">Session assurance</span>
          <h2>One voter identity. One selected event.</h2>
          <p>Your selected event is kept in this browser session and never published with voter identity.</p>
        </div>
        <button className="button button--light" type="button" onClick={onEndSession}>
          <Icon name="logout" size={17} />
          End Session
        </button>
      </aside>
    </section>
  );
}
