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

export interface GameStateResponse {
  status: GameStatus;
  turn: number;
  max_turns: number;
  guesses: GuessEntry[];
  candidate_count: number;
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
