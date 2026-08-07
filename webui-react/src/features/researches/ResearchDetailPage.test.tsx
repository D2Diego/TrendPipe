import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResearchDetailPage } from "./ResearchDetailPage";
import * as researchApi from "@/api/research";

function renderAtId(id: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>
    <MemoryRouter initialEntries={[`/researches/${id}`]}>
      <Routes><Route path="/researches/:id" element={<ResearchDetailPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>);
}

const base = {
  id: "r1", topic: "cats", depth: "quick" as const, sources: ["reddit"],
  created_at: "", updated_at: "", error_message: null, report_json: null,
};

describe("ResearchDetailPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows non-terminal status while polling", async () => {
    vi.spyOn(researchApi, "getResearch").mockResolvedValue({ ...base, status: "running" });
    renderAtId("r1");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("running"));
  });

  it("shows the failure message", async () => {
    vi.spyOn(researchApi, "getResearch").mockResolvedValue({ ...base, status: "failed", error_message: "boom" });
    renderAtId("r1");
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("boom"));
  });

  it("shows cluster rank, explanation, and evidence links", async () => {
    vi.spyOn(researchApi, "getResearch").mockResolvedValue({
      ...base,
      status: "completed",
      report_json: { entities: [{ entity: "cats", report: {
        clusters: [{ cluster_id: "cluster-1", title: "Cats are great", score: 55, sources: ["reddit"], candidate_ids: ["candidate-1"] }],
        ranked_candidates: [{ candidate_id: "candidate-1", cluster_id: "cluster-1", title: "Evidence", url: "https://example.com/cats", explanation: "Strong engagement" }],
      } }] },
    });
    renderAtId("r1");

    await waitFor(() => expect(screen.getByText("Cats are great")).toBeInTheDocument());
    expect(screen.getByText("Strong engagement")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Evidence" })).toHaveAttribute("href", "https://example.com/cats");
  });

  it("offers artifact generation for a completed cluster, and shows saved artifacts read-only", async () => {
    vi.spyOn(researchApi, "getResearch").mockResolvedValue({
      ...base,
      status: "completed",
      report_json: { entities: [{ entity: "cats", report: {
        clusters: [
          { cluster_id: "cluster-1", title: "Cats are great", candidate_ids: [] },
          { cluster_id: "cluster-2", title: "Cats vs dogs", candidate_ids: [] },
        ],
        ranked_candidates: [],
      } }] },
      artifacts: [{
        id: "a1", research_id: "r1", entity: "cats", cluster_id: "cluster-1",
        video_subject: "Why cats are great", video_script: null, video_script_prompt: null,
        custom_system_prompt: null, video_terms: null, generated_fields: [],
        created_at: "", updated_at: "",
      }],
    });
    renderAtId("r1");

    await waitFor(() => expect(screen.getByText("Cats vs dogs")).toBeInTheDocument());
    expect(screen.getByText("Why cats are great")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Generate artifacts" })).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Use artifacts" })).toBeInTheDocument();
  });
});
