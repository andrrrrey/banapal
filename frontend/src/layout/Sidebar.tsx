import { NavLink } from "react-router-dom";

import { NAV_ITEMS, NAV_SECTIONS } from "./navConfig";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo">B</div>
        <div>
          <b>Banapal</b>
          <span>Контроль лидов и аналитика</span>
        </div>
      </div>

      <nav className="nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section}>
            <div className="nav-label">{section}</div>
            {NAV_ITEMS.filter((i) => i.section === section).map((item) => {
              const { Icon } = item;
              return (
                <NavLink key={item.key} to={item.path} className={({ isActive }) => (isActive ? "active" : "")}>
                  <Icon />
                  {item.label}
                  {item.badge ? <span className="badge">{item.badge}</span> : null}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="side-foot">
        <b>Демо-данные</b>
        <br />
        Этап 1 · единая система контроля и аналитики
      </div>
    </aside>
  );
}
