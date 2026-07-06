import type { GuessEntry, TileState } from "../types";

export type KeyState = TileState | "unused";

const RANK: Record<KeyState, number> = {
  unused: 0,
  gray: 1,
  yellow: 2,
  green: 3,
};

/** Each letter shows its best-known state across all guesses (green > yellow > gray). */
export function deriveKeyStates(guesses: GuessEntry[]): Map<string, KeyState> {
  const states = new Map<string, KeyState>();
  for (const { word, feedback } of guesses) {
    for (let i = 0; i < word.length; i++) {
      const letter = word[i];
      const next = feedback[i];
      const prev = states.get(letter) ?? "unused";
      if (RANK[next] > RANK[prev]) states.set(letter, next);
    }
  }
  return states;
}
