import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as researchApi from "@/api/research";
import { useGenerationStore } from "@/store/generationStore";
import { ArtifactChat } from "./ArtifactChat";

const ARTIFACT = {
  id: "a1",
  research_id: "r1",
  entity: "cats",
  cluster_id: "cluster-1",
  video_subject: "Why cats are great",
  video_script: null,
  video_script_prompt: null,
  custom_system_prompt: null,
  video_terms: null,
  generated_fields: [] as researchApi.ArtifactField[],
  created_at: "",
  updated_at: "",
};

function renderChat(props: Partial<Parameters<typeof ArtifactChat>[0]> = {}) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={["/researches/r1"]}>
          <Routes>
            <Route path="/researches/:id" element={<ArtifactChat researchId="r1" entity="cats" clusterId="cluster-1" {...props} />} />
            <Route path="/generate" element={<div data-testid="generate-screen" />} />
          </Routes>
        </MemoryRouter>
      </I18nextProvider>
    </QueryClientProvider>,
  );
}

describe("ArtifactChat", () => {
  afterEach(() => { vi.restoreAllMocks(); useGenerationStore.getState().reset(); });

  it("interviews the user and shows the agent's question", async () => {
    vi.spyOn(researchApi, "postArtifactChat").mockResolvedValue({ type: "question", message: "Who is the audience?" });
    renderChat();

    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate artifacts") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Continue") }));

    await waitFor(() => expect(screen.getByText(/Who is the audience\?/)).toBeInTheDocument());
    expect(researchApi.postArtifactChat).toHaveBeenCalledWith("r1", "cats", "cluster-1", ["video_subject"], []);
  });

  it("includes optional fields once selected and sends the transcript on reply", async () => {
    vi.spyOn(researchApi, "postArtifactChat")
      .mockResolvedValueOnce({ type: "question", message: "Who is the audience?" })
      .mockResolvedValueOnce({ type: "final", message: "Ready", artifact: { ...ARTIFACT, generated_fields: ["video_script"] } });
    renderChat();

    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate artifacts") }));
    fireEvent.click(screen.getByRole("checkbox", { name: i18n.t("Video Script") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Continue") }));
    await waitFor(() => expect(screen.getByText(/Who is the audience\?/)).toBeInTheDocument());
    expect(researchApi.postArtifactChat).toHaveBeenCalledWith("r1", "cats", "cluster-1", ["video_subject", "video_script"], []);

    fireEvent.change(screen.getByLabelText(i18n.t("Your reply")), { target: { value: "General audience, concise." } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Send") }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Ready"));
    expect(researchApi.postArtifactChat).toHaveBeenLastCalledWith(
      "r1", "cats", "cluster-1", ["video_subject", "video_script"],
      [{ role: "assistant", content: "Who is the audience?" }, { role: "user", content: "General audience, concise." }],
    );
  });

  it("shows a chat-level error without losing the conversation", async () => {
    vi.spyOn(researchApi, "postArtifactChat").mockRejectedValue(new Error("LLM unavailable"));
    renderChat();

    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate artifacts") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Continue") }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("LLM unavailable"));
  });

  it("offers to use or regenerate artifacts once one already exists", () => {
    renderChat({ artifact: ARTIFACT });
    expect(screen.getByText("Why cats are great")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: i18n.t("Use artifacts") })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: i18n.t("Generate again") })).toBeInTheDocument();
  });

  it("loads restored params into the generation store and navigates to /generate", async () => {
    vi.spyOn(researchApi, "getArtifactRestoreParams").mockResolvedValue({ params: { video_subject: "Restored subject" } });
    renderChat({ artifact: ARTIFACT });

    fireEvent.click(screen.getByRole("button", { name: i18n.t("Use artifacts") }));

    await waitFor(() => expect(screen.getByTestId("generate-screen")).toBeInTheDocument());
    expect(useGenerationStore.getState().params.video_subject).toBe("Restored subject");
  });
});
