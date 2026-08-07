import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Field, Input, Select } from "./field";

describe("Field/Input/Select", () => {
  it("uses theme tokens for input and select", () => {
    render(<><Input aria-label="input" /><Select aria-label="select"><option>a</option></Select></>);
    expect(screen.getByLabelText("input")).toHaveClass("bg-background");
    expect(screen.getByLabelText("select")).toHaveClass("bg-background");
  });

  it("uses muted help text", () => {
    render(<Field label="Label" htmlFor="x" help="help"><Input id="x" /></Field>);
    expect(screen.getByText("help")).toHaveClass("text-muted-foreground");
  });
});
