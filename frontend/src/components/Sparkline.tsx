import { useId } from "react";

// SVG-спарклайн (перенос из прототипа).
export function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 64;
  const h = 24;
  const mx = Math.max(...data);
  const mn = Math.min(...data);
  const r = mx - mn || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, h - 2 - ((v - mn) / r) * (h - 4)]);
  const path = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = `${path} L${w} ${h} L0 ${h} Z`;
  const id = useId().replace(/:/g, "");

  return (
    <svg width={w} height={h}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity=".22" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
