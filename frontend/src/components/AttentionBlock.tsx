import type { Attention } from "@/api/dashboard";
import { useDrill } from "./useDrill";

const TILE_ICONS: Record<string, string> = {
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2" stroke-linecap="round"/>',
  task: '<path d="M9 11l3 3 8-8M20 12v6a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h9" stroke-linecap="round" stroke-linejoin="round"/>',
  freeze: '<path d="M12 2v20M4 7l16 10M20 7L4 17" stroke-linecap="round"/>',
  touch: '<path d="M8 11V6a2 2 0 114 0v5m0-3a2 2 0 114 0v3m0-1a2 2 0 114 0v4a6 6 0 01-6 6h-2a6 6 0 01-5-2.7L7 16" stroke-linecap="round" stroke-linejoin="round"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5" stroke-linecap="round" stroke-linejoin="round"/>',
  romi: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M9 10c0-1 1-1.6 3-1.6s3 .6 3 1.8c0 2.4-6 1.2-6 3.6 0 1.2 1 1.8 3 1.8s3-.6 3-1.6" stroke-linecap="round"/>',
  plug: '<path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 01-10 0zM12 16v6" stroke-linecap="round" stroke-linejoin="round"/>',
};

export function AttentionBlock({ data }: { data: Attention }) {
  const { toDrill, toRiskLeads } = useDrill();

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-h">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h3>Что требует внимания сейчас</h3>
          <span className="live"><span className="p" />по данным на текущий момент</span>
        </div>
      </div>
      <div className="att-grid">
        <div className="att-head">
          <div className="att-money" onClick={() => toDrill("monitor:stuck")}>
            <span className="aml">Деньги под риском сейчас</span>
            <span className="amv num">{data.money_at_risk_display}</span>
            <span className="ams">просроченные сделки с известной суммой</span>
          </div>
          <div className="att-leads" onClick={toRiskLeads}>
            <span className="aml">Лиды с риском потери</span>
            <span className="amv num">{data.risk_leads}</span>
            <span className="ams">нажмите, чтобы отфильтровать список лидов</span>
          </div>
        </div>
        <div className="att-tiles">
          {data.tiles.map((t, i) => (
            <div key={i} className={`att-tile ${t.cls}`} onClick={() => toDrill(t.drill)}>
              <div className="att-ic">
                <svg
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                  dangerouslySetInnerHTML={{ __html: TILE_ICONS[t.icon] ?? "" }}
                />
              </div>
              <div className="att-n num">{t.n}</div>
              <div className="att-l">{t.label}</div>
              <div className="att-s">{t.sub}</div>
              <div className="att-go">Перейти →</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
