import { useCallback, useEffect, useRef, useState } from "react";
import { hardwareApi } from "../api/client";
import { fmtPct } from "../lib/grover";
import type { HardwareInfo, HardwareJob, HardwareJobStatus } from "../types";

const TERMINAL: ReadonlySet<HardwareJobStatus> = new Set<HardwareJobStatus>([
  "DONE",
  "CANCELLED",
  "ERROR",
]);

const STATUS_LABEL: Record<HardwareJobStatus, string> = {
  INITIALIZING: "準備中",
  QUEUED: "キュー待ち",
  RUNNING: "実行中",
  DONE: "完了",
  CANCELLED: "キャンセルされました",
  ERROR: "エラー",
};

/** Queues are shared, so poll gently and back off once it is clearly not instant. */
const POLL_FAST_MS = 3000;
const POLL_SLOW_MS = 10000;
const BACKOFF_AFTER_MS = 30000;

function StateBars({ job }: { job: HardwareJob }) {
  const scale = Math.max(
    ...job.states.map((s) =>
      Math.max(s.ideal_probability, s.hardware_probability ?? 0),
    ),
    1e-9,
  );

  return (
    <div className="flex flex-col gap-1.5" data-testid="hardware-states">
      {job.states.map((s) => (
        <div key={s.index} className="flex items-center gap-2">
          <span className="w-14 shrink-0 truncate text-right font-mono text-xs text-fg/80">
            {s.word ?? `|${s.index}⟩`}
          </span>
          <div className="flex flex-1 flex-col gap-0.5">
            <div className="h-2 overflow-hidden rounded-sm bg-ink">
              <div
                className="h-full bg-cyan/40 transition-all duration-500"
                style={{ width: `${(s.ideal_probability / scale) * 100}%` }}
              />
            </div>
            <div className="h-2 overflow-hidden rounded-sm bg-ink">
              <div
                className={`h-full transition-all duration-500 ${
                  s.is_marked
                    ? "bg-gradient-to-r from-cyan to-violet"
                    : "bg-tile-yellow"
                }`}
                style={{
                  width: `${((s.hardware_probability ?? 0) / scale) * 100}%`,
                }}
              />
            </div>
          </div>
          <span className="w-24 shrink-0 font-mono text-[10px] text-muted">
            {fmtPct(s.ideal_probability)} →{" "}
            <span className={s.is_marked ? "text-fg" : "text-tile-yellow"}>
              {s.hardware_probability === null
                ? "—"
                : fmtPct(s.hardware_probability)}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function HardwareLab({ gameId }: { gameId: string }) {
  const [info, setInfo] = useState<HardwareInfo | null>(null);
  const [job, setJob] = useState<HardwareJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timer = useRef<number | null>(null);
  // Bumped whenever an in-flight poll chain becomes stale (new submit, new
  // game, unmount), so late responses from the old chain are dropped.
  const generation = useRef(0);

  const stopPolling = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    hardwareApi
      .info()
      .then((res) => {
        if (active) setInfo(res);
      })
      .catch(() => {
        // Hardware mode is optional: a failed probe just hides the panel.
        if (active) setInfo(null);
      });
    return () => {
      active = false;
    };
  }, []);

  // A hardware job costs real QPU time and minutes of queue, so it is NOT
  // discarded when the player takes another turn — the shortlist it ran against
  // stays on screen. Only a brand-new game invalidates it.
  useEffect(() => {
    generation.current += 1;
    stopPolling();
    setJob(null);
    setError(null);
  }, [gameId, stopPolling]);

  useEffect(() => {
    return () => {
      generation.current += 1;
      stopPolling();
    };
  }, [stopPolling]);

  const poll = useCallback(
    (jobId: string, gen: number, startedAt: number) => {
      const delay =
        Date.now() - startedAt > BACKOFF_AFTER_MS ? POLL_SLOW_MS : POLL_FAST_MS;
      timer.current = window.setTimeout(() => {
        timer.current = null;
        if (gen !== generation.current) return;
        hardwareApi
          .job(jobId)
          .then((next) => {
            if (gen !== generation.current) return;
            setJob(next);
            if (!TERMINAL.has(next.status)) poll(jobId, gen, startedAt);
          })
          .catch((e: unknown) => {
            if (gen !== generation.current) return;
            setError(
              e instanceof Error ? e.message : "ジョブの取得に失敗しました",
            );
          });
      }, delay);
    },
    [],
  );

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    stopPolling();
    const gen = ++generation.current;
    try {
      const created = await hardwareApi.submit(gameId);
      if (gen !== generation.current) return;
      setJob(created);
      poll(created.job_id, gen, Date.now());
    } catch (e) {
      if (gen === generation.current) {
        setError(e instanceof Error ? e.message : "実機への投入に失敗しました");
      }
    } finally {
      if (gen === generation.current) setSubmitting(false);
    }
  };

  if (!info?.available) return null;

  const pending = job !== null && !TERMINAL.has(job.status);
  const noiseGap =
    job?.hardware_marked_probability != null
      ? job.ideal_marked_probability - job.hardware_marked_probability
      : null;

  return (
    <aside
      className="w-full rounded-xl border border-line bg-surface p-5"
      aria-busy={pending}
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-sm font-bold tracking-widest text-muted uppercase">
          実機モード — IBM Quantum QPU
        </h2>
        <span className="font-mono text-xs text-muted">
          {job?.backend ?? info.configured_backend ?? "least busy QPU"}
        </span>
      </div>

      <div className="grid gap-x-6 gap-y-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div className="flex flex-col gap-3">
          <p className="text-xs leading-relaxed text-muted">
            ゲーム本体の12量子ビットのオラクルは、トランスパイルすると数万ゲートの深さになり
            実機ではノイズに埋もれます。そこで候補の上位 最大 {info.shortlist_size}{" "}
            語(2の冪に丸め)を 2〜4 量子ビットの空間に詰め直し、候補の割合を 1/4
            にして <span className="font-mono">k = 1</span>{" "}
            回で済む浅い回路にしたものを実機に投げます。理想値はちょうど 100%
            なので、差分はそのまま装置のノイズです。
          </p>

          <button
            onClick={() => void submit()}
            disabled={submitting || pending}
            className="rounded-md bg-gradient-to-r from-cyan to-violet px-3 py-2 font-display text-sm font-bold text-ink hover:brightness-110 focus-visible:outline-2 focus-visible:outline-cyan disabled:opacity-50"
          >
            {submitting ? "投入中…" : pending ? "実行待ち…" : "実機で測定する"}
          </button>

          <p className="font-mono text-[10px] text-muted">
            共有の無料枠を使うため 1時間 {info.max_jobs_per_hour} 件 / 1日{" "}
            {info.max_jobs_per_day} 件まで(直近 {info.jobs_last_hour} /{" "}
            {info.jobs_last_day} 件)
          </p>

          {error && <p className="text-xs text-tile-yellow">{error}</p>}

          {job && (
            <dl
              className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-[11px]"
              aria-live="polite"
            >
              <dt className="text-muted">状態</dt>
              <dd>
                {STATUS_LABEL[job.status]}
                {pending && ` (${Math.round(job.elapsed_seconds)}s 経過)`}
              </dd>
              <dt className="text-muted">回路</dt>
              <dd>
                {job.n_qubits} qubits / depth {job.depth} / 2Q {job.two_qubit_gates}
              </dd>
              <dt className="text-muted">shots</dt>
              <dd>{job.shots.toLocaleString()}</dd>
              {job.qpu_seconds !== null && (
                <>
                  <dt className="text-muted">QPU時間</dt>
                  <dd>{job.qpu_seconds.toFixed(2)}s</dd>
                </>
              )}
              <dt className="text-muted">job</dt>
              <dd className="truncate">{job.job_id}</dd>
            </dl>
          )}

          {job?.error && <p className="text-xs text-tile-yellow">{job.error}</p>}
        </div>

        {job && job.status === "DONE" ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 font-mono text-sm">
              <span>
                P(候補) 理想{" "}
                <span className="text-cyan">
                  {fmtPct(job.ideal_marked_probability)}
                </span>
              </span>
              <span>
                実機{" "}
                <span className="text-violet">
                  {job.hardware_marked_probability === null
                    ? "—"
                    : fmtPct(job.hardware_marked_probability)}
                </span>
                {noiseGap !== null && (
                  <span className="text-muted">
                    {" "}
                    (ノイズ −{fmtPct(noiseGap)})
                  </span>
                )}
              </span>
            </div>
            <p className="font-mono text-[10px] text-muted">
              上段 = 理想(シミュレータ) / 下段 = 実機。
              <span className="text-tile-yellow">黄色</span>{" "}
              は候補でない状態に漏れた確率。
            </p>
            <StateBars job={job} />
          </div>
        ) : (
          <p className="hidden text-xs leading-relaxed text-muted lg:block">
            {pending
              ? "実機のキューに入りました。結果が返るまで数分〜数十分かかることがあります。このまま置いておけば自動で更新されます。"
              : "「実機で測定する」を押すと、同じGroverアルゴリズムを実機のQPUで走らせ、理想分布と並べて比較します。"}
          </p>
        )}
      </div>
    </aside>
  );
}
