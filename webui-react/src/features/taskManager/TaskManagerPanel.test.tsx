import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as api from "@/api/taskHistory";
import { TaskManagerPanel } from "./TaskManagerPanel";

describe("TaskManagerPanel", () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.spyOn(api, "listTaskHistory").mockResolvedValue({ tasks: [{ task_id: "p1", subject: "processing", state: 4, progress: 40 }, { task_id: "c1", subject: "complete", state: 1, progress: 100, video_file: "c1/final-0.mp4" }] }); });
  it("shows processing badge and four filters", async () => {
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><TaskManagerPanel /></I18nextProvider></QueryClientProvider>);
    const trigger = await screen.findByRole("button", { name: /Task Manager · 1/ });
    fireEvent.click(trigger);
    await waitFor(() => expect(screen.getAllByRole("tab")).toHaveLength(4));
    expect(screen.getByText("processing")).toBeInTheDocument();
  });
  it("opens inline video preview", async () => {
    render(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><TaskManagerPanel /></I18nextProvider></QueryClientProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Task Manager/ }));
    const playButtons = await screen.findAllByRole("button", { name: i18n.t("Play") });
    fireEvent.click(playButtons.find((button) => !button.hasAttribute("disabled"))!);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
