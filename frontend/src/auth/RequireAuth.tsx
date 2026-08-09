import { Spin } from "antd";
import { Navigate, Outlet } from "react-router-dom";

import { useMe } from "@/api/auth";

// Гейт авторизации: неавторизованных отправляем на /login.
export function RequireAuth() {
  const me = useMe();

  if (me.isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!me.data) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
