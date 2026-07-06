import type { KeyState } from "../lib/keyStates";

const ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];

const KEY_BG: Record<KeyState, string> = {
  unused: "bg-surface text-fg",
  gray: "bg-tile-gray text-muted",
  yellow: "bg-tile-yellow text-fg",
  green: "bg-tile-green text-fg",
};

export function Keyboard({
  keyStates,
  onKey,
  disabled,
}: {
  keyStates: Map<string, KeyState>;
  onKey: (key: string) => void;
  disabled: boolean;
}) {
  const keyClass =
    "h-12 rounded-md font-display font-bold uppercase transition-colors " +
    "hover:brightness-125 focus-visible:outline-2 focus-visible:outline-cyan " +
    "disabled:opacity-40 disabled:hover:brightness-100";

  return (
    <div className="flex flex-col items-center gap-1.5" data-testid="keyboard">
      {ROWS.map((row, i) => (
        <div key={row} className="flex gap-1.5">
          {i === 2 && (
            <button
              className={`${keyClass} bg-surface px-3 text-xs`}
              onClick={() => onKey("Enter")}
              disabled={disabled}
            >
              Enter
            </button>
          )}
          {[...row].map((k) => (
            <button
              key={k}
              className={`${keyClass} w-8 sm:w-10 ${KEY_BG[keyStates.get(k) ?? "unused"]}`}
              onClick={() => onKey(k)}
              disabled={disabled}
            >
              {k}
            </button>
          ))}
          {i === 2 && (
            <button
              className={`${keyClass} bg-surface px-3`}
              onClick={() => onKey("Backspace")}
              disabled={disabled}
              aria-label="Backspace"
            >
              ⌫
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
