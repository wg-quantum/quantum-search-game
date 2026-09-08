import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { info, submit, job } = vi.hoisted(() => ({
  info: vi.fn(),
  submit: vi.fn(),
  job: vi.fn(),
}));

vi.mock("../api/client", async (importActual) => {
  const actual = await importActual<typeof import("../api/client")>();
  return { ...actual, hardwareApi: { info, submit, job } };
});

import { ApiError } from "../api/client";
import type { HardwareJob, HardwareJobStatus } from "../types";
import { HardwareLab } from "./HardwareLab";

const INFO = {
  available: true,
  reason: null,
  configured_backend: null,
  shortlist_size: 4,
  shots: 1024,
  max_jobs_per_hour: 3,
  max_jobs_per_day: 10,
  jobs_last_hour: 0,
  jobs_last_day: 0,
};

function makeJob(
  status: HardwareJobStatus,
  overrides: Partial<HardwareJob> = {},
): HardwareJob {
  const marked = [0, 4, 8, 12];
  return {
    job_id: "job-1",
    status,
    backend: "ibm_fake",
    n_qubits: 4,
    n_states: 16,
    iterations: 1,
    shots: 1024,
    depth: 23,
    two_qubit_gates: 14,
    shortlist: ["crane", "slate", "audio", "raise"],
    ideal_marked_probability: 1.0,
    hardware_marked_probability: null,
    states: Array.from({ length: 16 }, (_, index) => ({
      index,
      word: marked.includes(index)
        ? ["crane", "slate", "audio", "raise"][marked.indexOf(index)]!
        : null,
      is_marked: marked.includes(index),
      ideal_probability: marked.includes(index) ? 0.25 : 0,
      hardware_probability: null,
      count: null,
    })),
    error: null,
    qpu_seconds: null,
    elapsed_seconds: 0,
  ...overrides,
  };
}

beforeEach(() => {
  info.mockReset().mockResolvedValue(INFO);
  submit.mockReset();
  job.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("HardwareLab", () => {
  it("renders nothing when the server has no IBM credentials", async () => {
    info.mockResolvedValue({ ...INFO, available: false, reason: "未設定" });
    const { container } = render(<HardwareLab gameId="g1" />);
    await waitFor(() => expect(info).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the availability probe fails", async () => {
    info.mockRejectedValue(new Error("network down"));
    const { container } = render(<HardwareLab gameId="g1" />);
    await waitFor(() => expect(info).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("submits a job, polls until DONE, and compares ideal against hardware", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    submit.mockResolvedValue(makeJob("QUEUED"));
    render(<HardwareLab gameId="g1" />);

    const button = await screen.findByRole("button", { name: "実機で測定する" });
    expect(screen.getByText(/1時間 3 件/)).toBeInTheDocument();

    fireEvent.click(button);
    await waitFor(() => expect(submit).toHaveBeenCalledWith("g1"));
    await screen.findByText(/キュー待ち/);

    // still queued: the panel keeps polling
    job.mockResolvedValueOnce(makeJob("RUNNING", { elapsed_seconds: 4 }));
    await vi.advanceTimersByTimeAsync(3000);
    await screen.findByText(/実行中/);

    const counts = [0, 4, 8, 12].map(() => 240);
    job.mockResolvedValueOnce(
      makeJob("DONE", {
        hardware_marked_probability: 0.9375,
        qpu_seconds: 2.5,
        elapsed_seconds: 30,
        states: makeJob("DONE").states.map((s) => ({
          ...s,
          hardware_probability: s.is_marked ? 0.234375 : 0.0078125,
          count: s.is_marked ? counts[0]! : 8,
        })),
      }),
    );
    await vi.advanceTimersByTimeAsync(3000);

    await screen.findByText("完了");
    expect(screen.getByText(/93\.8%/)).toBeInTheDocument();
    expect(screen.getByText(/ノイズ −6\.3%/)).toBeInTheDocument();
    expect(screen.getByText("2.50s")).toBeInTheDocument();
    expect(screen.getByTestId("hardware-states").children).toHaveLength(16);

    // terminal state: polling stops
    const pollCount = job.mock.calls.length;
    await vi.advanceTimersByTimeAsync(30000);
    expect(job).toHaveBeenCalledTimes(pollCount);
  });

  it("surfaces the quota error from the API", async () => {
    submit.mockRejectedValue(
      new ApiError("rate_limited", "実機ジョブは1時間に3件までです"),
    );
    render(<HardwareLab gameId="g1" />);
    fireEvent.click(await screen.findByRole("button", { name: "実機で測定する" }));

    expect(
      await screen.findByText("実機ジョブは1時間に3件までです"),
    ).toBeInTheDocument();
    // the button stays usable so the player can retry later
    expect(screen.getByRole("button", { name: "実機で測定する" })).toBeEnabled();
  });

  it("stops polling after unmount", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    submit.mockResolvedValue(makeJob("QUEUED"));
    job.mockResolvedValue(makeJob("QUEUED"));
    const { unmount } = render(<HardwareLab gameId="g1" />);

    fireEvent.click(await screen.findByRole("button", { name: "実機で測定する" }));
    await waitFor(() => expect(submit).toHaveBeenCalled());

    unmount();
    await vi.advanceTimersByTimeAsync(30000);
    expect(job).not.toHaveBeenCalled();
  });
});
