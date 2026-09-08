export type TileState = "green" | "yellow" | "gray";
export type GameStatus = "playing" | "won" | "lost";

export interface CreateGameResponse {
  game_id: string;
  max_turns: number;
  word_length: number;
  dictionary_size: number;
}

export interface GuessEntry {
  word: string;
  feedback: TileState[];
}

export interface GuessResponse {
  feedback: TileState[];
  status: GameStatus;
  turn: number;
  candidate_count: number;
}

export interface CandidatesResponse {
  total: number;
  words: string[];
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}

export interface StateProb {
  index: number;
  word: string | null;
  probability: number;
  is_candidate: boolean;
}

export interface Snapshot {
  iteration: number;
  top: StateProb[];
  others_probability: number;
  candidate_probability: number;
}

export interface QuantumRunResponse {
  n_qubits: number;
  n_states: number;
  candidate_count: number;
  optimal_iterations: number;
  iterations: number;
  snapshots: Snapshot[];
}

export interface MeasureResult {
  index: number;
  word: string | null;
  is_candidate: boolean;
  count: number;
}

export interface QuantumMeasureResponse {
  iterations: number;
  shots: number;
  results: MeasureResult[];
}

export interface CircuitResponse {
  iterations: number;
  drawn_iterations: number;
  svg: string;
}

// ---- hardware mode (IBM Quantum QPU) ----

export interface HardwareInfo {
  available: boolean;
  reason: string | null;
  configured_backend: string | null;
  shortlist_size: number;
  shots: number;
  max_jobs_per_hour: number;
  max_jobs_per_day: number;
  jobs_last_hour: number;
  jobs_last_day: number;
}

export type HardwareJobStatus =
  | "INITIALIZING"
  | "QUEUED"
  | "RUNNING"
  | "DONE"
  | "CANCELLED"
  | "ERROR";

export interface HardwareStateProb {
  index: number;
  /** null = padding state, present only to dilute the candidates to 1/4. */
  word: string | null;
  is_marked: boolean;
  ideal_probability: number;
  hardware_probability: number | null;
  count: number | null;
}

export interface HardwareJob {
  job_id: string;
  status: HardwareJobStatus;
  backend: string;
  n_qubits: number;
  n_states: number;
  iterations: number;
  shots: number;
  depth: number;
  two_qubit_gates: number;
  shortlist: string[];
  ideal_marked_probability: number;
  hardware_marked_probability: number | null;
  states: HardwareStateProb[];
  error: string | null;
  qpu_seconds: number | null;
  elapsed_seconds: number;
}
