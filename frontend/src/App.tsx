import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "./api/client";
import { Board } from "./components/Board";
import { CandidatePanel } from "./components/CandidatePanel";
import { QuantumLab } from "./components/QuantumLab";
import { Keyboard } from "./components/Keyboard";
import { Tutorial } from "./components/Tutorial";
import { deriveKeyStates } from "./lib/keyStates";
import type { GameStatus, GuessEntry } from "./types";

interface Meta {
  gameId: string;
  maxTurns: number;
  wordLength: number;
  dictionarySize: number;
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [guesses, setGuesses] = useState<GuessEntry[]>([]);
  const [status, setStatus] = useState<GameStatus>("playing");
  const [current, setCurrent] = useState("");
  const [candidateCount, setCandidateCount] = useState(0);
  const [candidateWords, setCandidateWords] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);
  const [fatal, setFatal] = useState<string | null>(null);
  const [showTutorial, setShowTutorial] = useState(
    () => localStorage.getItem("qw-tutorial-seen") !== "1",
  );
  const submitting = useRef(false);

  const closeTutorial = useCallback(() => {
    localStorage.setItem("qw-tutorial-seen", "1");
    setShowTutorial(false);
  }, []);

  const newGame = useCallback(async () => {
    try {
      const res = await api.createGame();
      setMeta({
        gameId: res.game_id,
        maxTurns: res.max_turns,
        wordLength: res.word_length,
        dictionarySize: res.dictionary_size,
      });
      setGuesses([]);
      setStatus("playing");
      setCurrent("");
      setMessage(null);
      setFatal(null);
      setCandidateCount(res.dictionary_size);
      const cands = await api.getCandidates(res.game_id);
      setCandidateWords(cands.words);
    } catch {
      setFatal("バックエンドに接続できません。`uvicorn app.main:app --port 8000` が起動しているか確認してください。");
    }
  }, []);

  useEffect(() => {
    void newGame();
  }, [newGame]);

  const showMessage = (text: string) => {
    setMessage(text);
    setShaking(true);
    window.setTimeout(() => setShaking(false), 400);
    window.setTimeout(() => setMessage(null), 2000);
  };

  const submit = useCallback(async () => {
    if (!meta || submitting.current) return;
    if (current.length !== meta.wordLength) {
      showMessage("5文字入力してください");
      return;
    }
    submitting.current = true;
    try {
      const res = await api.postGuess(meta.gameId, current);
      setGuesses((g) => [...g, { word: current, feedback: res.feedback }]);
      setStatus(res.status);
      setCandidateCount(res.candidate_count);
      setCurrent("");
      const cands = await api.getCandidates(meta.gameId);
      setCandidateWords(cands.words);
    } catch (e) {
      if (e instanceof ApiError && e.code === "unknown_word") {
        showMessage("辞書にない単語です");
      } else {
        showMessage(e instanceof Error ? e.message : "エラーが発生しました");
      }
    } finally {
      submitting.current = false;
    }
  }, [meta, current]);

  const handleKey = useCallback(
    (key: string) => {
      if (!meta || status !== "playing") return;
      if (key === "Enter") {
        void submit();
      } else if (key === "Backspace") {
        setCurrent((c) => c.slice(0, -1));
      } else if (/^[a-z]$/i.test(key)) {
        setCurrent((c) =>
          c.length < meta.wordLength ? c + key.toLowerCase() : c,
        );
      }
    },
    [meta, status, submit],
  );

  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      handleKey(e.key);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [handleKey]);

  const keyStates = useMemo(() => deriveKeyStates(guesses), [guesses]);

  if (fatal) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        {showTutorial && <Tutorial onClose={closeTutorial} />}
        <p className="max-w-md rounded-xl border border-line bg-surface p-6 text-sm leading-relaxed">
          {fatal}
        </p>
      </main>
    );
  }

  if (!meta) return null;

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col items-center gap-6 p-4 sm:p-6">
      {showTutorial && <Tutorial onClose={closeTutorial} />}
      <header className="flex w-full items-center justify-between border-b border-line pb-4">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            Quantum <span className="bg-gradient-to-r from-cyan to-violet bg-clip-text text-transparent">Wordle</span>
          </h1>
          <p className="text-xs text-muted">
            Grover Algorithm を体験して学ぶ Wordle
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-md border border-line px-3 py-1.5 font-display text-sm font-bold hover:bg-surface focus-visible:outline-2 focus-visible:outline-cyan"
            onClick={() => setShowTutorial(true)}
          >
            使い方
          </button>
          <button
            className="rounded-md border border-line px-3 py-1.5 font-display text-sm font-bold hover:bg-surface focus-visible:outline-2 focus-visible:outline-cyan"
            onClick={() => void newGame()}
          >
            新しいゲーム
          </button>
        </div>
      </header>

      <div className="flex w-full flex-col items-center gap-6 lg:flex-row lg:items-start lg:justify-center">
        <section className="flex flex-col items-center gap-5">
          <div className="relative">
            {message && (
              <div className="absolute -top-10 left-1/2 z-10 -translate-x-1/2 rounded-md bg-fg px-3 py-1.5 text-sm font-bold whitespace-nowrap text-ink">
                {message}
              </div>
            )}
            <Board
              guesses={guesses}
              current={current}
              maxTurns={meta.maxTurns}
              wordLength={meta.wordLength}
              shaking={shaking}
            />
          </div>

          {status !== "playing" && (
            <p className="font-display text-lg font-bold" data-testid="result">
              {status === "won"
                ? `正解! 候補が ${candidateCount} 語まで絞れていました`
                : "6ターン終了。候補パネルの中に正解がいます"}
            </p>
          )}

          <Keyboard
            keyStates={keyStates}
            onKey={handleKey}
            disabled={status !== "playing"}
          />
        </section>

        <div className="flex w-full flex-col gap-6 lg:w-80">
          <CandidatePanel
            count={candidateCount}
            total={meta.dictionarySize}
            words={candidateWords}
          />
          <QuantumLab
            gameId={meta.gameId}
            candidateCount={candidateCount}
            guessCount={guesses.length}
            playing={status === "playing"}
            onSuggest={(word) => setCurrent(word)}
          />
        </div>
      </div>
    </main>
  );
}
