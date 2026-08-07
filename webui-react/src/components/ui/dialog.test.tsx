import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Dialog } from "./dialog";

describe("Dialog", () => {
  it("renders only while open", () => {
    const { rerender } = render(<Dialog open={false} onClose={vi.fn()} title="Test">content</Dialog>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    rerender(<Dialog open onClose={vi.fn()} title="Test">content</Dialog>);
    expect(screen.getByRole("dialog", { name: "Test" })).toBeInTheDocument();
  });

  it("closes from backdrop and Escape, but not panel clicks", () => {
    const onClose = vi.fn();
    render(<Dialog open onClose={onClose} title="Test">content</Dialog>);
    fireEvent.click(screen.getByText("content"));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("dialog-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
