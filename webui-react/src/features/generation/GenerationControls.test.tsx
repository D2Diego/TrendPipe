import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import * as videosApi from "@/api/videos";
import { useGenerationStore } from "@/store/generationStore";
import { GenerationControls } from "./GenerationControls";

const readiness = { pexels: true, pixabay: true, coverr: true, sonilo: true, elevenlabs: true };
describe("GenerationControls", () => {
  beforeEach(() => { void i18n.changeLanguage("en"); vi.restoreAllMocks(); useGenerationStore.getState().reset(); vi.spyOn(configApi, "getGenerationReadiness").mockResolvedValue(readiness); vi.spyOn(configApi, "getUiConfig").mockResolvedValue({ hide_log: true }); });
  it("blocks invalid requests before video task creation", async () => {
    const create = vi.spyOn(videosApi, "createVideoTask");
    render(<QueryClientProvider client={new QueryClient()}><GenerationControls /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate Video") }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });
  it("submits a valid request and starts task progress", async () => {
    useGenerationStore.getState().setParam("video_subject", "cats");
    vi.spyOn(videosApi, "createVideoTask").mockResolvedValue({ task_id: "task-123", request_id: "req", params: useGenerationStore.getState().params });
    vi.spyOn(videosApi, "getTaskStatus").mockResolvedValue({ task_id: "task-123", state: 4, progress: 5 });
    render(<QueryClientProvider client={new QueryClient()}><GenerationControls /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Generate Video") }));
    await waitFor(() => expect(useGenerationStore.getState().currentGenerationTaskId).toBe("task-123"));
  });
});
