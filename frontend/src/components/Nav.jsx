import { NavLink } from "react-router-dom";
import Icon from "./Icon";

const items = [
  { to: "/dashboard", label: "Election Events", icon: "home" },
  { to: "/ballot", label: "Referendum Ballot", icon: "ballot" },
  { to: "/receipt", label: "Vote Receipt", icon: "receipt" },
  { to: "/board", label: "Public Board", icon: "board" },
  { to: "/tally", label: "Tally Dashboard", icon: "tally" }
];

export default function Nav({ currentPath, isAuthenticated, onLogout }) {
  return (
    <nav className="nav" aria-label="Primary">
      <span className="nav__label">Portal</span>
      {items.map((item) => {
        const active =
          currentPath === item.to ||
          (item.to === "/ballot" &&
            (currentPath === "/camera" || currentPath === "/biometric-verify"));
        return (
          <NavLink className={active ? "is-active" : ""} key={item.to} to={item.to}>
            <Icon name={item.icon} size={19} />
            <span>{item.label}</span>
            {active ? <i /> : null}
          </NavLink>
        );
      })}
      {isAuthenticated ? (
        <button className="nav__logout" type="button" onClick={onLogout}>
          <Icon name="logout" size={19} />
          <span>End Session</span>
        </button>
      ) : null}
    </nav>
  );
}
