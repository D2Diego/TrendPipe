import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiPost } from "./client";

describe("API client", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn()));

  it("unwraps successful response envelopes", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: 200, data: { foo: "bar" } }), { status: 200 }));
    await expect(apiGet<{ foo: string }>("/providers/llm")).resolves.toEqual({ foo: "bar" });
  });

  it("surfaces the backend message on errors", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: 400, message: "bad request" }), { status: 400 }));
    await expect(apiGet("/voices")).rejects.toEqual(expect.objectContaining({ status: 400, message: "bad request" }));
  });

  it("posts JSON payloads", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: 200, data: { ok: true } }), { status: 200 }));
    await apiPost("/videos", { video_subject: "cats" });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/v1/videos", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ video_subject: "cats" }),
    }));
  });
});
