import { fireEvent, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import type { TaskSummary } from "@/api/taskHistory";
import { TaskTable } from "./TaskTable";

const task: TaskSummary = { task_id: "t1", subject: "cats", state: 1, progress: 100, mtime: 1700000000, video_file: "t1/final-0.mp4" };
describe("TaskTable", () => {
  it("renders tasks and invokes actions", () => {
    const onPlay = vi.fn(); const onRegenerate = vi.fn(); const onDelete = vi.fn();
    render(<I18nextProvider i18n={i18n}><TaskTable tasks={[task]} onPlay={onPlay} onRegenerate={onRegenerate} onDelete={onDelete} /></I18nextProvider>);
    expect(screen.getByText("cats")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Play") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Regenerate") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Delete Task") }));
    expect(onPlay).toHaveBeenCalledWith(task); expect(onRegenerate).toHaveBeenCalledWith("t1"); expect(onDelete).toHaveBeenCalledWith("t1");
  });
  it("shows empty state and disables unavailable play", () => {
    const props = { onPlay: vi.fn(), onRegenerate: vi.fn(), onDelete: vi.fn() };
    const view = render(<I18nextProvider i18n={i18n}><TaskTable tasks={[]} {...props} /></I18nextProvider>);
    expect(screen.getByText(i18n.t("No Tasks Match Filter"))).toBeInTheDocument();
    view.rerender(<I18nextProvider i18n={i18n}><TaskTable tasks={[{ ...task, video_file: "" }]} {...props} /></I18nextProvider>);
    expect(screen.getByRole("button", { name: i18n.t("Play") })).toBeDisabled();
  });
});
