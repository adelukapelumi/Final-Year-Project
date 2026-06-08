import Nav from "./Nav";

export default function Layout({ children, currentPath, isAuthenticated, onLogout }) {
  return (
    <div className="shell">
      <div className="shell__inner">
        <header className="topbar">
          <div className="brand">
            <h1>Diaspora Voting MVP</h1>
            <p>Simple referendum frontend for the existing Flask voting API.</p>
          </div>
          <Nav currentPath={currentPath} isAuthenticated={isAuthenticated} onLogout={onLogout} />
        </header>

        <main>{children}</main>
      </div>
    </div>
  );
}
