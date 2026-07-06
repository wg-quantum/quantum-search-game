import type { GuessEntry, TileState } from "../types";

const TILE_BG: Record<TileState, string> = {
  green: "bg-tile-green border-tile-green",
  yellow: "bg-tile-yellow border-tile-yellow",
  gray: "bg-tile-gray border-tile-gray",
};

function Tile({
  letter,
  state,
  delay,
}: {
  letter: string;
  state?: TileState;
  delay?: number;
}) {
  const base =
    "flex h-13 w-13 items-center justify-center rounded-md border-2 font-display text-2xl font-bold uppercase select-none";
  if (state) {
    return (
      <div
        className={`${base} ${TILE_BG[state]} tile-flip text-fg`}
        style={{ animationDelay: `${delay ?? 0}ms` }}
      >
        {letter}
      </div>
    );
  }
  return (
    <div className={`${base} ${letter ? "border-muted" : "border-line"} bg-transparent`}>
      {letter}
    </div>
  );
}

export function Board({
  guesses,
  current,
  maxTurns,
  wordLength,
  shaking,
}: {
  guesses: GuessEntry[];
  current: string;
  maxTurns: number;
  wordLength: number;
  shaking: boolean;
}) {
  const rows = [];
  for (let r = 0; r < maxTurns; r++) {
    const guess = guesses[r];
    const isCurrent = r === guesses.length;
    const tiles = [];
    for (let c = 0; c < wordLength; c++) {
      tiles.push(
        guess ? (
          <Tile key={c} letter={guess.word[c]} state={guess.feedback[c]} delay={c * 90} />
        ) : (
          <Tile key={c} letter={isCurrent ? (current[c] ?? "") : ""} />
        ),
      );
    }
    rows.push(
      <div
        key={r}
        className={`flex gap-1.5 ${isCurrent && shaking ? "row-shake" : ""}`}
        data-testid={`row-${r}`}
      >
        {tiles}
      </div>,
    );
  }
  return <div className="flex flex-col gap-1.5">{rows}</div>;
}
