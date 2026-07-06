import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Board } from "./Board";
import { CandidatePanel } from "./CandidatePanel";
import { Tutorial } from "./Tutorial";

describe("Board", () => {
  it("renders max_turns rows and shows feedback tiles", () => {
    render(
      <Board
        guesses={[
          { word: "crane", feedback: ["gray", "yellow", "gray", "green", "gray"] },
        ]}
        current="po"
        maxTurns={6}
        wordLength={5}
        shaking={false}
      />,
    );
    for (let r = 0; r < 6; r++) {
      expect(screen.getByTestId(`row-${r}`)).toBeInTheDocument();
    }
    expect(screen.getByText("c")).toBeInTheDocument();
    // current input row shows typed letters
    expect(screen.getByText("p")).toBeInTheDocument();
    expect(screen.getByText("o")).toBeInTheDocument();
  });
});

describe("CandidatePanel", () => {
  it("shows count, total and overflow indicator", () => {
    render(
      <CandidatePanel count={120} total={2315} words={["crane", "brave"]} />,
    );
    expect(screen.getByTestId("candidate-count")).toHaveTextContent("120");
    expect(screen.getByText("crane")).toBeInTheDocument();
    expect(screen.getByText("+118")).toBeInTheDocument();
  });
});

import { AmplitudeChart } from "./AmplitudeChart";

describe("AmplitudeChart", () => {
  it("renders words, padding-state kets and percentages", () => {
    render(
      <AmplitudeChart
        snapshot={{
          iteration: 2,
          top: [
            { index: 10, word: "crane", probability: 0.4, is_candidate: true },
            { index: 3000, word: null, probability: 0.001, is_candidate: false },
          ],
          others_probability: 0.599,
          candidate_probability: 0.4,
        }}
      />,
    );
    expect(screen.getByText("crane")).toBeInTheDocument();
    expect(screen.getByText("|3000⟩")).toBeInTheDocument();
    expect(screen.getByText("40.0%")).toBeInTheDocument();
  });
});

describe("Tutorial", () => {
  it("steps through and drives home the core misconception", () => {
    render(<Tutorial onClose={() => {}} />);
    expect(screen.getByText("これは何のゲーム?")).toBeInTheDocument();
    expect(screen.getByText("1 / 5")).toBeInTheDocument();

    // advance to the "Grover doesn't know the answer" step
    fireEvent.click(screen.getByRole("button", { name: "次へ" }));
    fireEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(screen.getByText("Grover は答えを知らない")).toBeInTheDocument();
  });

  it("closes on the last step and via the close button", () => {
    const onClose = vi.fn();
    render(<Tutorial onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "チュートリアルを閉じる" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
