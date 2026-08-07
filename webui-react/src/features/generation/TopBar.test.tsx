import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import i18n from "@/i18n";
import { TopBar } from "./TopBar";

describe("TopBar", () => {
  beforeEach(() => i18n.changeLanguage("en"));
  const renderTopBar = (initialEntry = "/") => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[initialEntry]}><TopBar /></MemoryRouter></QueryClientProvider>);
  it("shows the TrendPipe brand without a brand link and changes language", () => {
    renderTopBar();
    expect(screen.getByText("TrendPipe")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /TrendPipe/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: i18n.t("Back") })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: i18n.t("Task Manager") })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Language / Languages"), { target: { value: "pt" } });
    expect(i18n.language).toBe("pt");
  });

  it("offers research from the generator and a way back home", () => {
    renderTopBar("/generate");
    expect(screen.getByRole("link", { name: i18n.t("Back") })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: i18n.t("Do Research") })).toHaveAttribute("href", "/researches");
    expect(screen.queryByRole("link", { name: i18n.t("Create Video") })).not.toBeInTheDocument();
  });

  it("offers video creation from research and returns details to the research list", () => {
    renderTopBar("/researches/r1");
    expect(screen.getByRole("link", { name: i18n.t("Back") })).toHaveAttribute("href", "/researches");
    expect(screen.getByRole("link", { name: i18n.t("Create Video") })).toHaveAttribute("href", "/generate");
    expect(screen.queryByRole("link", { name: i18n.t("Do Research") })).not.toBeInTheDocument();
  });
  it("opens Settings", () => {
    renderTopBar();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Settings") }));
    expect(screen.getByRole("dialog", { name: i18n.t("Settings") })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(5);
  });

  it("opens the researcher settings tab from the URL", async () => {
    renderTopBar("/researches?settings=researcher");
    expect(await screen.findByRole("dialog", { name: i18n.t("Settings") })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: i18n.t("Researcher Settings Tab") })).toHaveAttribute("aria-selected", "true");
  });
});
