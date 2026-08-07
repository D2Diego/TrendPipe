import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Tabs } from "./tabs";

describe("Tabs", () => {
  const tabs = [{ key: "a", label: "Tab A", content: "Content A" }, { key: "b", label: "Tab B", content: "Content B" }];
  it("shows the first tab and switches on click", () => {
    render(<Tabs tabs={tabs} />);
    expect(screen.getByText("Content A")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Tab A" })).toHaveAttribute("aria-selected", "true");
    fireEvent.click(screen.getByRole("tab", { name: "Tab B" }));
    expect(screen.getByText("Content B")).toBeInTheDocument();
    expect(screen.queryByText("Content A")).not.toBeInTheDocument();
  });
});
