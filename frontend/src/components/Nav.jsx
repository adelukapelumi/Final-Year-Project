import { NavLink } from "react-router-dom";

export default function Nav({ currentPath, isAuthenticated, onLogout }) {
  return (
    <nav className="nav" aria-label="Primary">
      <NavLink className={currentPath === "/login" ? "is-active" : ""} to="/login">
        Login
      </NavLink>
      <NavLink className={currentPath === "/ballot" ? "is-active" : ""} to="/ballot">
        Ballot
      </NavLink>
      <NavLink className={currentPath === "/receipt" ? "is-active" : ""} to="/receipt">
        Receipt
      </NavLink>
      <NavLink className={currentPath === "/board" ? "is-active" : ""} to="/board">
        Public Board
      </NavLink>
      <NavLink className={currentPath === "/tally" ? "is-active" : ""} to="/tally">
        Tally
      </NavLink>
      {isAuthenticated ? (
        <button type="button" onClick={onLogout}>
          Logout
        </button>
      ) : null}
    </nav>
  );
}
