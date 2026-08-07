import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createResearch,
  deleteArtifact,
  deleteResearch,
  getArtifactRestoreParams,
  getResearch,
  getResearchSettings,
  listResearches,
  postArtifactChat,
  updateResearchSettings,
} from "./research";

function mockResponse(data: unknown) {
  return new Response(JSON.stringify({ status: 200, data }), { status: 200 });
}

describe("research API client", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn()));

  it("lists researches", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ researches: [{ id: "r1" }] }));
    await expect(listResearches()).resolves.toEqual({ researches: [{ id: "r1" }] });
    expect(fetch).toHaveBeenCalledWith("/api/v1/researches");
  });

  it("creates, gets, and deletes a research", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ id: "r1", status: "pending" }));
    await createResearch({ topic: "cats", depth: "quick", sources: ["reddit"] });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ topic: "cats", depth: "quick", sources: ["reddit"] }),
    }));

    vi.mocked(fetch).mockResolvedValue(mockResponse({ id: "r1", status: "completed" }));
    await expect(getResearch("r1")).resolves.toEqual({ id: "r1", status: "completed" });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches/r1");

    vi.mocked(fetch).mockResolvedValue(mockResponse({ deleted: true }));
    await deleteResearch("r1");
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches/r1", { method: "DELETE" });
  });

  it("gets and updates research settings", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ available_sources: ["reddit"] }));
    await expect(getResearchSettings()).resolves.toEqual({ available_sources: ["reddit"] });

    vi.mocked(fetch).mockResolvedValue(mockResponse({ saved: true }));
    await updateResearchSettings({ OPENROUTER_API_KEY: "abc" });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/research-settings", expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ values: { OPENROUTER_API_KEY: "abc" } }),
    }));
  });

  it("posts an artifact chat turn", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ type: "question", message: "Who is the audience?" }));
    const messages = [{ role: "user" as const, content: "General audience" }];
    await expect(postArtifactChat("r1", "cats", "cluster-1", ["video_subject"], messages))
      .resolves.toEqual({ type: "question", message: "Who is the audience?" });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches/r1/entities/cats/clusters/cluster-1/artifact-chat", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ selected_fields: ["video_subject"], messages }),
    }));
  });

  it("gets restore params and deletes an artifact", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ params: { video_subject: "Cats" } }));
    await expect(getArtifactRestoreParams("r1", "cats", "cluster-1")).resolves.toEqual({ params: { video_subject: "Cats" } });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches/r1/entities/cats/clusters/cluster-1/restore-params");

    vi.mocked(fetch).mockResolvedValue(mockResponse({ deleted: true }));
    await deleteArtifact("r1", "cats", "cluster-1");
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/researches/r1/entities/cats/clusters/cluster-1/artifacts", { method: "DELETE" });
  });
});
