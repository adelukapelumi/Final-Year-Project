import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import { fetchTally } from "../api";

export default function Dashboard({ session }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let active = true;
    fetchTally()
      .then((result) => {
        if (active) {
          setStats(result);
        }
      })
      .catch(() => {
        if (active) {
          setStats(null);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const profile = session?.profile || {};

  return (
    <section className="page voter-dashboard">
      <div className="dashboard-welcome">
        <div>
          <span className="section-kicker">Authenticated voter portal</span>
          <h1>Welcome, {profile.displayName?.split(" ")[0] || "Voter"}.</h1>
          <p>Your accreditation is complete. Review the active referendum event below.</p>
        </div>
        <div className="dashboard-identity">
          {session?.capturedImage ? <img src={session.capturedImage} alt="Session profile" /> : null}
          <div>
            <strong>{profile.displayName || "Verified Voter"}</strong>
            <span><Icon name="map" size={14} /> {profile.diasporaLocation || "Diaspora"}</span>
          </div>
          <span className="status-badge status-badge--success"><Icon name="check" size={13} /> Verified</span>
        </div>
      </div>

      <div className="dashboard-stat-grid">
        <article>
          <span className="dashboard-stat__icon"><Icon name="user" /></span>
          <div><small>Prototype voters</small><strong>{stats?.total_registered_voters ?? "4"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--mint"><Icon name="ballot" /></span>
          <div><small>Ballots cast</small><strong>{stats?.total_ballots_cast ?? "—"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--gold"><Icon name="clock" /></span>
          <div><small>Election status</small><strong>{stats?.status || "Active"}</strong></div>
        </article>
        <article>
          <span className="dashboard-stat__icon dashboard-stat__icon--navy"><Icon name="camera" /></span>
          <div><small>Verification mode</small><strong>Camera prototype</strong></div>
        </article>
      </div>

      <div className="dashboard-grid">
        <article className="event-card">
          <div className="event-card__visual">
            <span className="event-card__ballot"><Icon name="ballot" size={38} /></span>
            <span className="event-card__ring" />
            <span className="event-card__ring event-card__ring--small" />
          </div>
          <div className="event-card__content">
            <div className="event-card__meta">
              <span className="status-badge status-badge--success">Active</span>
              <span>Binary referendum</span>
            </div>
            <h2>Diaspora Voting Referendum</h2>
            <p>Should secure diaspora voting be enabled for eligible Nigerians abroad?</p>
            <dl>
              <div><dt>Ballot type</dt><dd>Binary referendum</dd></div>
              <div><dt>Status</dt><dd>Active</dd></div>
              <div><dt>Eligibility</dt><dd><Icon name="check" size={14} /> Verified</dd></div>
            </dl>
            <Link className="button button--primary" to="/ballot">
              Proceed to Ballot
              <Icon name="arrow" size={18} />
            </Link>
          </div>
        </article>

        <aside className="dashboard-side-card">
          <span className="icon-tile"><Icon name="shield" /></span>
          <span className="section-kicker">Session assurance</span>
          <h2>Ready to vote privately.</h2>
          <p>Your camera frame remains in this browser session and is never published with your ballot.</p>
          <div><Icon name="check" size={16} /> NIN eligibility confirmed</div>
          <div><Icon name="check" size={16} /> Face presence verified</div>
          <div><Icon name="check" size={16} /> Ballot access unlocked</div>
        </aside>
      </div>
    </section>
  );
}
