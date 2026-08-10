import { Button } from "antd";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { useLogout, useMe } from "@/api/auth";
import { useDataSource } from "@/api/integrations";
import { NAV_ITEMS } from "./navConfig";

function useMoscowClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const time = new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  }).format(now);
  const date = new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    weekday: "short",
    timeZone: "Europe/Moscow",
  }).format(now);
  return { time, date };
}

export function Topbar() {
  const location = useLocation();
  const { time, date } = useMoscowClock();
  const logout = useLogout();
  const me = useMe();
  const ds = useDataSource();
  const isReal = ds.data?.data_source === "real";

  const item = NAV_ITEMS.find((i) => location.pathname.startsWith(i.path)) ?? NAV_ITEMS[0];

  return (
    <header className="topbar">
      <div className="page-title">
        <h1>{item.label}</h1>
        <p>{item.subtitle}</p>
      </div>
      <div className="spacer" />
      <div className={`demo-pill${isReal ? " live" : ""}`}>
        <span className="dot" />
        {isReal ? "Боевые интеграции" : "Демо-данные"}
      </div>
      <div className="clock">
        <b>{time}</b>
        <br />
        <span>{date} · МСК</span>
      </div>
      <Button size="small" onClick={() => logout.mutate()} loading={logout.isPending}>
        Выйти{me.data ? ` · ${me.data.login}` : ""}
      </Button>
    </header>
  );
}
