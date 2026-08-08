import * as echarts from "echarts";
import { useEffect, useRef } from "react";

// Обёртка над Apache ECharts: инициализация, обновление опций, авто-resize.
export function EChart({ option, height = 280 }: { option: echarts.EChartsOption; height?: number }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!el.current) return;
    chart.current = echarts.init(el.current);
    const onResize = () => chart.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, true);
    chart.current?.resize();
  }, [option]);

  return <div ref={el} style={{ width: "100%", height }} />;
}
