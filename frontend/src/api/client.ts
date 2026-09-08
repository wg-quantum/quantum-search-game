import type {
  ApiErrorBody,
  CandidatesResponse,
  CircuitResponse,
  CreateGameResponse,
  GuessResponse,
  HardwareInfo,
  HardwareJob,
  QuantumMeasureResponse,
  QuantumRunResponse,
} from "../types";

const BASE = "/api/v1";

export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      body?.error?.code ?? "unknown",
      body?.error?.message ?? `HTTP ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  createGame: () =>
    request<CreateGameResponse>("/games", { method: "POST" }),

  postGuess: (gameId: string, word: string) =>
    request<GuessResponse>(`/games/${gameId}/guesses`, {
      method: "POST",
      body: JSON.stringify({ word }),
    }),

  getCandidates: (gameId: string, limit = 60, offset = 0) =>
    request<CandidatesResponse>(
      `/games/${gameId}/candidates?limit=${limit}&offset=${offset}`,
    ),
};

export const quantumApi = {
  run: (gameId: string, iterations: number) =>
    request<QuantumRunResponse>(
      `/games/${gameId}/quantum/run`,
      { method: "POST", body: JSON.stringify({ iterations }) },
    ),

  measure: (gameId: string, iterations: number, shots = 1) =>
    request<QuantumMeasureResponse>(
      `/games/${gameId}/quantum/measure`,
      { method: "POST", body: JSON.stringify({ iterations, shots }) },
    ),
};

export const circuitApi = {
  get: (gameId: string, iterations: number) =>
    request<CircuitResponse>(
      `/games/${gameId}/quantum/circuit?iterations=${iterations}`,
    ),
};

export const hardwareApi = {
  /** Whether a QPU is reachable. Does no network I/O server-side, so it is cheap. */
  info: () => request<HardwareInfo>("/quantum/hardware"),

  /** Enqueue one downscaled Grover job. Returns while it is still queued. */
  submit: (gameId: string) =>
    request<HardwareJob>(`/games/${gameId}/quantum/hardware`, {
      method: "POST",
    }),

  job: (jobId: string) => request<HardwareJob>(`/quantum/jobs/${jobId}`),
};
