import { describe, expect, it } from "vitest";
import { deriveKeyStates } from "./keyStates";

describe("deriveKeyStates", () => {
  it("returns empty map with no guesses", () => {
    expect(deriveKeyStates([]).size).toBe(0);
  });

  it("assigns states per letter", () => {
    const states = deriveKeyStates([
      { word: "crane", feedback: ["gray", "yellow", "gray", "green", "gray"] },
    ]);
    expect(states.get("c")).toBe("gray");
    expect(states.get("r")).toBe("yellow");
    expect(states.get("n")).toBe("green");
    expect(states.get("z")).toBeUndefined();
  });

  it("upgrades yellow to green across guesses, never downgrades", () => {
    const states = deriveKeyStates([
      { word: "route", feedback: ["yellow", "gray", "gray", "gray", "gray"] },
      { word: "prank", feedback: ["gray", "green", "gray", "gray", "gray"] },
      { word: "randy", feedback: ["gray", "gray", "gray", "gray", "gray"] },
    ]);
    expect(states.get("r")).toBe("green");
  });

  it("duplicate letters in one guess keep the best state", () => {
    const states = deriveKeyStates([
      { word: "eerie", feedback: ["gray", "green", "gray", "gray", "yellow"] },
    ]);
    expect(states.get("e")).toBe("green");
  });
});
