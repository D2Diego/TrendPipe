import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Popover } from "./popover";

describe("Popover", () => {
  it("shows content only when open and closes outside", () => {
    const onOpenChange = vi.fn();
    render(<div><Popover open onOpenChange={onOpenChange} trigger={<button>Open</button>}>content</Popover><span data-testid="outside">outside</span></div>);
    expect(screen.getByText("content")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByTestId("outside"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
