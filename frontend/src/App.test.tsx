import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createGame, postGuess, getCandidates } = vi.hoisted(() => ({
  createGame: vi.fn(),
  postGuess: vi.fn(),
  getCandidates: vi.fn(),
}));

vi.mock("./api/client", async (importActual) => {
  const actual = await importActual<typeof import("./api/client")>();
  return { ...actual, api: { createGame, postGuess, getCandidates } };
});

import { ApiError } from "./api/client";
import App from "./App";

function type(word: string) {
  for (const ch of word) fireEvent.keyDown(window, { key: ch });
}

beforeEach(() => {
  localStorage.setItem("qw-tutorial-seen", "1"); // skip the tutorial modal
  createGame.mockReset().mockResolvedValue({
    game_id: "g1",
    max_turns: 6,
    word_length: 5,
    dictionary_size: 2315,
  });
  getCandidates.mockReset().mockResolvedValue({ total: 2315, words: ["crane"] });
  postGuess.mockReset();
});

describe("App", () => {
  it("submits a keyboard guess and shows the win result", async () => {
    postGuess.mockResolvedValue({
      feedback: ["green", "green", "green", "green", "green"],
      status: "won",
      turn: 1,
      candidate_count: 1,
    });
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("row-0")).toBeInTheDocument());

    type("crane");
    fireEvent.keyDown(window, { key: "Enter" });

    await waitFor(() =>
      expect(postGuess).toHaveBeenCalledWith("g1", "crane"),
    );
    expect(await screen.findByTestId("result")).toHaveTextContent("正解");
  });

  it("shows a friendly message when the word is not in the dictionary", async () => {
    postGuess.mockRejectedValue(new ApiError("unknown_word", "not in dict"));
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("row-0")).toBeInTheDocument());

    type("zzzzz");
    fireEvent.keyDown(window, { key: "Enter" });

    expect(await screen.findByText("辞書にない単語です")).toBeInTheDocument();
  });

  it("starts a fresh game when 新しいゲーム is clicked", async () => {
    render(<App />);
    await waitFor(() => expect(createGame).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "新しいゲーム" }));
    await waitFor(() => expect(createGame).toHaveBeenCalledTimes(2));
  });
});
