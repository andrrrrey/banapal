import { Outlet } from "react-router-dom";

import { FilterBar } from "./FilterBar";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  return (
    <div className="app">
      <Sidebar />
      <div className="main">
        <Topbar />
        <FilterBar />
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
