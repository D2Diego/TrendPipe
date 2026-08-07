import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { TopBar } from "./TopBar";

describe("TopBar", () => {
  beforeEach(() => i18n.changeLanguage("en"));
  const renderTopBar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><TopBar /></QueryClientProvider>);
  it("exposes the page actions and changes language", () => {
    renderTopBar();
    expect(screen.getByRole("link", { name: /MoneyPrinterTurbo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: i18n.t("Task Manager") })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Language / Languages"), { target: { value: "pt" } });
    expect(i18n.language).toBe("pt");
  });
  it("opens Settings", () => {
    renderTopBar();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Settings") }));
    expect(screen.getByRole("dialog", { name: i18n.t("Settings") })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(4);
  });
});
