// Модульная сборка ECharts: подключаем только используемые графики и компоненты,
// чтобы не тянуть весь пакет (существенно ускоряет production-сборку).
import { BarChart, FunnelChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { init, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

use([
  BarChart, LineChart, PieChart, FunnelChart, ScatterChart,
  GridComponent, TooltipComponent, LegendComponent,
  CanvasRenderer,
]);

export { init };
