import type { Kpi } from "@/api/dashboard";
import { Sparkline } from "./Sparkline";
import { useDrill } from "./useDrill";

function trendArrow(trend: string) {
  return trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
}
function sparkColor(trend: string) {
  return trend === "down" ? "#12B76A" : trend === "warn" ? "#F79009" : "#635BFF";
}

export function KpiRow({ cards }: { cards: Kpi[] }) {
  const { toDrill } = useDrill();
  return (
    <div className="grid kpis">
      {cards.map((c) => (
        <div
          key={c.key}
          className={`card kpi ${c.drill ? "kpi-click" : ""}`}
          onClick={c.drill ? () => toDrill(c.drill) : undefined}
        >
          <div className="top">
            <div className={`ic ${c.icon}`}>
              <svg
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
                dangerouslySetInnerHTML={{ __html: c.svg }}
              />
            </div>
            <span className="lab">{c.label}</span>
          </div>
          <div className="val num">{c.display}</div>
          <div className="foot">
            <span className={`chip ${c.trend}`}>
              {trendArrow(c.trend)} {c.delta}
            </span>
            <span className="vs">{c.period_label}</span>
          </div>
          <div className="spark">
            <Sparkline data={c.spark} color={sparkColor(c.trend)} />
          </div>
        </div>
      ))}
    </div>
  );
}
