import { beforeEach, describe, expect, it, vi } from "vitest";
import { deleteConfigValue, getConfigSection, setConfigValue } from "./config";

describe("generalized config API", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 200, data: { ok: true } }) })));
  it("gets any config section", async () => {
    await getConfigSection("azure");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/config/azure"));
  });
  it("sets and deletes section values", async () => {
    await setConfigValue("azure", "speech_key", "secret");
    let [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ value: "secret" });
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls[1][1].method).toBe("POST");
    await deleteConfigValue("azure", "speech_key");
    [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[2];
    expect(init.method).toBe("DELETE");
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls[3][1].method).toBe("POST");
  });
});
