import type { EChartsOption } from "echarts";
import { useEffect, useRef } from "react";

import { init } from "@/echarts";

type ChartInstance = ReturnType<typeof init>;
type CoreOption = Parameters<ChartInstance["setOption"]>[0];

// Обёртка над Apache ECharts: инициализация, обновление опций, авто-resize.
export function EChart({ option, height = 280 }: { option: EChartsOption; height?: number }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<ChartInstance | null>(null);

  useEffect(() => {
    if (!el.current) return;
    chart.current = init(el.current);
    const onResize = () => chart.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option as CoreOption, true);
    chart.current?.resize();
  }, [option]);

  return <div ref={el} style={{ width: "100%", height }} />;
}
