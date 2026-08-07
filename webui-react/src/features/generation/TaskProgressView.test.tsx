import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as configApi from "@/api/config";
import * as videosApi from "@/api/videos";
import { useGenerationStore } from "@/store/generationStore";
import { TaskProgressView } from "./TaskProgressView";

describe("TaskProgressView", () => {
  beforeEach(() => { void i18n.changeLanguage("en"); vi.restoreAllMocks(); useGenerationStore.getState().reset(); vi.spyOn(configApi, "getUiConfig").mockResolvedValue({ hide_log: false }); });
  it("shows progress and captured logs for a running task", async () => {
    useGenerationStore.getState().setCurrentGenerationTaskId("task-1");
    vi.spyOn(videosApi, "getTaskStatus").mockResolvedValue({ task_id: "task-1", state: 4, progress: 42 });
    vi.spyOn(videosApi, "getTaskLogs").mockResolvedValue({ logs: ["line one"] });
    render(<QueryClientProvider client={new QueryClient()}><TaskProgressView /></QueryClientProvider>);
    await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42"));
    expect(await screen.findByText("line one")).toBeInTheDocument();
  });
  it("renders video and download links when complete", async () => {
    useGenerationStore.getState().setCurrentGenerationTaskId("task-2");
    vi.spyOn(videosApi, "getTaskStatus").mockResolvedValue({ task_id: "task-2", state: 1, progress: 100, videos: ["/api/v1/video.mp4"] });
    vi.spyOn(videosApi, "getTaskLogs").mockResolvedValue({ logs: [] });
    render(<QueryClientProvider client={new QueryClient()}><TaskProgressView /></QueryClientProvider>);
    expect(await screen.findByRole("link", { name: i18n.t("Download Video") })).toBeInTheDocument();
  });
});
