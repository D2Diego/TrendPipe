import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Panel } from "./Panel";

describe("Panel", () => {
  it("uses card theme tokens", () => {
    render(<Panel title="Test">content</Panel>);
    expect(screen.getByText("Test").closest("section")).toHaveClass("bg-card");
  });
});
