import { NavLink } from "react-router-dom";
import { getActiveProjectId } from "../project";

const links: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Gaps", end: true },
  { to: "/coverage", label: "Coverage" },
  { to: "/evaluate", label: "Evaluate" },
  { to: "/shadow", label: "Shadow" },
  { to: "/runs", label: "Runs" },
  { to: "/continuation", label: "Continuation" },
  { to: "/setup", label: "Setup" },
];

export function Nav() {
  const projectId = getActiveProjectId();
  return (
    <nav className="nav" aria-label="Primary">
      <div className="nav-inner">
        <span className="nav-brand">Content Gap Intelligence</span>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            {l.label}
          </NavLink>
        ))}
        <span className="nav-spacer" />
        {projectId && (
          <span className="nav-project" title="Active project id">
            project: {projectId.slice(0, 8)}…
          </span>
        )}
      </div>
    </nav>
  );
}
