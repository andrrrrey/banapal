import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { FiltersProvider } from "@/state/filters";
import { FilterBar } from "./FilterBar";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  // Закрываем мобильный drawer при переходе между разделами.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <FiltersProvider>
      <div className={`app${navOpen ? " nav-open" : ""}`}>
        <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
        {navOpen ? <div className="nav-scrim" onClick={() => setNavOpen(false)} /> : null}
        <div className="main">
          <Topbar onMenu={() => setNavOpen(true)} />
          <FilterBar />
          <div className="content">
            <Outlet />
          </div>
        </div>
      </div>
    </FiltersProvider>
  );
}
