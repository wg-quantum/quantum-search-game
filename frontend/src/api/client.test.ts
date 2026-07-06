import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./client";

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client error handling", () => {
  it("maps the error envelope onto ApiError", async () => {
    mockFetch(422, { error: { code: "unknown_word", message: "nope" } });
    await expect(api.postGuess("g1", "zzzzz")).rejects.toMatchObject({
      code: "unknown_word",
      message: "nope",
    });
  });

  it("does not throw while constructing the error when body lacks `error`", async () => {
    // Malformed/empty error body must not mask the failure with a TypeError.
    mockFetch(500, {});
    const err = await api.createGame().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("unknown");
    expect(err.message).toBe("HTTP 500");
  });

  it("returns parsed JSON on success", async () => {
    mockFetch(201, {
      game_id: "abc",
      max_turns: 6,
      word_length: 5,
      dictionary_size: 2315,
    });
    await expect(api.createGame()).resolves.toMatchObject({ game_id: "abc" });
  });
});
