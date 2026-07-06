import { describe, expect, it } from "vitest";
import { fmtPct, sliderMax } from "./grover";

describe("sliderMax", () => {
  it("gives at least 6 when optimum is tiny (large candidate sets)", () => {
    expect(sliderMax(0)).toBe(6);
    expect(sliderMax(1)).toBe(6);
  });
  it("covers 3x the optimum for over-rotation", () => {
    expect(sliderMax(50)).toBe(150);
  });
  it("respects the server hard cap", () => {
    expect(sliderMax(90)).toBe(200);
  });
});

describe("fmtPct", () => {
  it("formats typical, tiny and full probabilities", () => {
    expect(fmtPct(0.955)).toBe("95.5%");
    expect(fmtPct(0.0004)).toBe("<0.1%");
    expect(fmtPct(0.99999)).toBe("100%");
    expect(fmtPct(0)).toBe("0.0%");
  });
});
