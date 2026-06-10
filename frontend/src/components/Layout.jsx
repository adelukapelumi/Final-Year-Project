import { Link } from "react-router-dom";
import Nav from "./Nav";
import Icon from "./Icon";

const publicPaths = new Set(["/", "/login", "/camera", "/board", "/tally"]);

function Brand() {
  return (
    <div className="brand">
      <span className="brand__mark">
        <Icon name="check" size={24} />
      </span>
      <span>
        <strong>Diaspora<span>Vote</span></strong>
        <small>Secure Binary Referendum Portal</small>
      </span>
    </div>
  );
}

export default function Layout({ children, currentPath, isAuthenticated, onLogout, session }) {
  if (publicPaths.has(currentPath)) {
    return (
      <div className="public-shell">
        <header className="public-header">
          <Link to="/" aria-label="DiasporaVote home"><Brand /></Link>
          <nav aria-label="Public">
            <Link to="/">Home</Link>
            <Link to="/board">Public Board</Link>
            <Link to="/tally">Tally</Link>
          </nav>
          {isAuthenticated && session?.biometricVerified ? (
            <Link className="button button--primary button--small" to="/dashboard">Dashboard</Link>
          ) : isAuthenticated ? (
            <Link className="button button--primary button--small" to="/camera">Accreditation Active</Link>
          ) : (
            <Link className="button button--outline button--small" to="/login">Start Accreditation</Link>
          )}
        </header>
        <main className="public-content">{children}</main>
        <footer className="public-footer">
          <span>© 2026 DiasporaVote prototype</span>
          <span><Icon name="lock" size={14} /> Privacy-preserving referendum portal</span>
        </footer>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />

        <div className="sidebar-profile">
          {session?.capturedImage ? (
            <img src={session.capturedImage} alt="" />
          ) : (
            <span>{session?.profile?.displayName?.slice(0, 1) || "V"}</span>
          )}
          <div>
            <strong>{session?.profile?.displayName || "Verified Voter"}</strong>
            <small>{session?.profile?.diasporaLocation || "Diaspora"}</small>
          </div>
        </div>

        <Nav currentPath={currentPath} isAuthenticated={isAuthenticated} onLogout={onLogout} />

        <div className="sidebar__security">
          <span className="icon-tile icon-tile--dark"><Icon name="shield" /></span>
          <strong>Ballot security</strong>
          <p>Protected by zero-knowledge proof verification.</p>
        </div>
      </aside>

      <div className="app-frame">
        <header className="mobile-header">
          <Brand />
          <span className="secure-chip"><Icon name="lock" size={14} /> Secure portal</span>
        </header>
        <main className="app-content">{children}</main>
        <footer className="app-footer">
          <span>© 2026 DiasporaVote prototype</span>
          <span><Icon name="lock" size={14} /> Secure binary referendum portal</span>
        </footer>
      </div>
    </div>
  );
}
