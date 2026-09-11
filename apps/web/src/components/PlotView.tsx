import Plot from "react-plotly.js";
import type { PlotlyFigure } from "../lib/api";

/** Replaceable visualization layer: this component owns the Plotly
 *  dependency. Swap it for an Observable/Vega/ECharts renderer without
 *  touching pages. */
export default function PlotView({ figure }: { figure: PlotlyFigure }) {
  return (
    <Plot
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      data={figure.data as any}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      layout={{ ...(figure.layout as any), autosize: true, paper_bgcolor: "#121a33", plot_bgcolor: "#0b1020", font: { color: "#e6ecff" } }}
      style={{ width: "100%", height: "380px" }}
      config={{ responsive: true }}
    />
  );
}
