import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("renders children and forwards standard button props", () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeDisabled();
  });

  it("defaults to the secondary themed variant", () => {
    render(<Button>Default</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-secondary");
  });

  it("applies and merges the primary variant", () => {
    render(<Button variant="primary" className="bg-destructive">Primary</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-destructive");
    expect(screen.getByRole("button")).not.toHaveClass("bg-primary");
  });
});
