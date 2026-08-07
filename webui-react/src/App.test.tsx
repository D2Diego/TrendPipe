import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the responsive generation grid", () => {
    render(<App />);
    expect(screen.getByTestId("main-settings-grid")).toBeInTheDocument();
  });
});
