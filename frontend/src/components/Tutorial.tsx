import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { TileState } from "../types";

const TILE_BG: Record<TileState, string> = {
  green: "bg-tile-green",
  yellow: "bg-tile-yellow",
  gray: "bg-tile-gray",
};

/** Small non-interactive tiles used to illustrate feedback in the tutorial. */
function MiniRow({ word, states }: { word: string; states: TileState[] }) {
  return (
    <div className="flex gap-1" aria-hidden="true">
      {word.split("").map((ch, i) => (
        <span
          key={i}
          className={`flex h-8 w-8 items-center justify-center rounded font-display text-sm font-bold uppercase text-fg ${TILE_BG[states[i]]}`}
        >
          {ch}
        </span>
      ))}
    </div>
  );
}

interface Step {
  title: string;
  body: ReactNode;
}

const STEPS: Step[] = [
  {
    title: "これは何のゲーム?",
    body: (
      <>
        <p>
          これは <strong className="text-fg">Wordle を解くためのゲームではありません</strong>。
          量子探索アルゴリズム <strong className="text-cyan">Grover</strong>（Oracle と
          振幅増幅）を、手を動かして直感的に理解するためのゲームです。
        </p>
        <p>
          Wordle の盤面は「Oracle に渡す条件」を作るための入口として使います。
        </p>
      </>
    ),
  },
  {
    title: "遊び方の基本",
    body: (
      <>
        <p>5 文字の単語を推測すると、各文字に色が付きます。</p>
        <div className="my-3 flex justify-center">
          <MiniRow word="crane" states={["gray", "yellow", "gray", "green", "gray"]} />
        </div>
        <ul className="space-y-1">
          <li>
            <span className="font-bold text-tile-green">緑</span> … 位置も文字も一致
          </li>
          <li>
            <span className="font-bold text-tile-yellow">黄</span> … 文字はあるが位置が違う
          </li>
          <li>
            <span className="font-bold text-muted">灰</span> … その文字は含まれない
          </li>
        </ul>
        <p className="mt-2">
          このフィードバックの積み重ねが、次のステップで Oracle が判定する
          <strong className="text-fg">「条件」</strong>になります。
        </p>
      </>
    ),
  },
  {
    title: "Grover は答えを知らない",
    body: (
      <>
        <p>
          ここが一番の誤解ポイントです。<strong className="text-fg">Oracle は正解の 1 語を
          知りません。</strong>
        </p>
        <p>
          Oracle がやるのは、<strong className="text-cyan">これまでのフィードバックと
          矛盾しない候補すべて</strong>に印（位相反転）を付けること —— つまり
          <strong className="text-fg">「条件を満たすか?」を判定する関数</strong>です。
        </p>
        <p>
          その印が付いた状態の振幅を、<strong className="text-violet">Diffusion</strong>
          が持ち上げます。この 2 つの繰り返しが Grover です。
        </p>
      </>
    ),
  },
  {
    title: "候補を絞るのはあなた",
    body: (
      <>
        <p>
          Grover は候補を<strong className="text-fg">等しく</strong>持ち上げるだけ。
          測定で正解を引く確率は、およそ <span className="font-mono text-cyan">1 / 候補数</span> です。
        </p>
        <p>
          だから確率を上げる一番の近道は、量子ではなく
          <strong className="text-fg">良い推測で候補そのものを減らすこと</strong>。
          右の候補パネルが減るほど、測定で正解に当たりやすくなります。
        </p>
      </>
    ),
  },
  {
    title: "回しすぎ注意（over-rotation）",
    body: (
      <>
        <p>
          「反復回数 <span className="font-mono">k</span> は多いほど良い」ではありません。
          最適値 <span className="font-mono text-cyan">k*</span> を超えると、振幅は行き過ぎて
          確率が<strong className="text-fg">再び下がります</strong>（over-rotation）。
        </p>
        <p>
          Grover Lab のスライダーで <span className="font-mono">k</span> を動かし、
          <strong className="text-violet">山を越えて確率が落ちていく</strong>様子を確かめてみてください。
        </p>
      </>
    ),
  },
];

export function Tutorial({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const isLast = step === STEPS.length - 1;
  const s = STEPS[step];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        className="measure-pop flex w-full max-w-md flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-baseline justify-between">
          <span className="font-mono text-xs tracking-widest text-muted">
            {step + 1} / {STEPS.length}
          </span>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="チュートリアルを閉じる"
            className="rounded p-1 text-muted hover:text-fg focus-visible:outline-2 focus-visible:outline-cyan"
          >
            ✕
          </button>
        </div>

        <h2
          id="tutorial-title"
          className="font-display text-xl font-bold tracking-tight"
        >
          {s.title}
        </h2>

        <div className="min-h-40 space-y-3 text-sm leading-relaxed text-muted">
          {s.body}
        </div>

        <div className="flex items-center gap-1.5" aria-hidden="true">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-gradient-to-r from-cyan to-violet" : "bg-line"}`}
            />
          ))}
        </div>

        <div className="flex justify-between gap-2">
          <button
            onClick={() => (step === 0 ? onClose() : setStep((n) => n - 1))}
            className="rounded-md border border-line px-4 py-2 font-display text-sm font-bold hover:bg-ink focus-visible:outline-2 focus-visible:outline-cyan"
          >
            {step === 0 ? "スキップ" : "戻る"}
          </button>
          <button
            onClick={() => (isLast ? onClose() : setStep((n) => n + 1))}
            className="rounded-md bg-gradient-to-r from-cyan to-violet px-5 py-2 font-display text-sm font-bold text-ink hover:brightness-110 focus-visible:outline-2 focus-visible:outline-cyan"
          >
            {isLast ? "はじめる" : "次へ"}
          </button>
        </div>
      </div>
    </div>
  );
}
