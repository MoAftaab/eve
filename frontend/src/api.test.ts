import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, clearSession, saveSession } from "./api";

describe("API client", () => {
  beforeEach(() => {
    vi.stubGlobal("sessionStorage", {
      getItem: vi.fn(() => "token"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it("adds bearer authentication and parses successful responses", async () => {
    vi.stubGlobal("fetch", vi.fn(async (_url: string, options: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, authorization: options.headers && (options.headers as Record<string, string>).Authorization }),
    })));
    await expect(api<{ ok: boolean; authorization: string }>("/health")).resolves.toEqual({ ok: true, authorization: "Bearer token" });
  });

  it("surfaces API error details", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 422, json: async () => ({ detail: "Invalid request" }) })));
    await expect(api("/bad")).rejects.toThrow("Invalid request");
  });

  it("explains network failures instead of exposing a browser fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(api("/health")).rejects.toThrow("Unable to reach the API");
  });

  it("manages the browser session", () => {
    const user = { id: "1", email: "a@b.com", full_name: "A", role: "PATIENT" as const };
    saveSession("token", user);
    expect(sessionStorage.setItem).toHaveBeenCalledWith("eve_token", "token");
    clearSession();
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("eve_token");
  });
});
