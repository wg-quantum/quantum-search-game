/** Slider range: reach ~1.5 oscillation periods so over-rotation and revival are visible. */
export function sliderMax(optimal: number, hardCap = 200): number {
  return Math.min(hardCap, Math.max(6, optimal * 3));
}

export function fmtPct(p: number): string {
  if (p >= 0.9995) return "100%";
  if (p < 0.001 && p > 0) return "<0.1%";
  return `${(p * 100).toFixed(1)}%`;
}
