import Nav from "./Nav";
import Icon from "./Icon";

export default function Layout({ children, currentPath, isAuthenticated, onLogout }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">
            <Icon name="check" size={24} />
          </span>
          <span>
            <strong>Diaspora<span>Vote</span></strong>
            <small>Secure Binary Referendum Portal</small>
          </span>
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
          <div className="brand">
            <span className="brand__mark"><Icon name="check" size={21} /></span>
            <span><strong>Diaspora<span>Vote</span></strong></span>
          </div>
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
