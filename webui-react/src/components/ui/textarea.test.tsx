import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Textarea } from "./textarea";

describe("Textarea", () => {
  it("uses theme tokens", () => {
    render(<Textarea aria-label="textarea" />);
    expect(screen.getByLabelText("textarea")).toHaveClass("bg-background");
  });
});
