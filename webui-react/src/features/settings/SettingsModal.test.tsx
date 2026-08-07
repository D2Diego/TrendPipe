import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { SettingsModal } from "./SettingsModal";

const renderModal = (open: boolean) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><I18nextProvider i18n={i18n}><SettingsModal open={open} onClose={vi.fn()} /></I18nextProvider></QueryClientProvider>);

describe("SettingsModal", () => {
  it("shows five tabs only while open", () => {
    const view = renderModal(false);
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    view.rerender(<QueryClientProvider client={new QueryClient()}><I18nextProvider i18n={i18n}><SettingsModal open onClose={vi.fn()} /></I18nextProvider></QueryClientProvider>);
    expect(screen.getAllByRole("tab")).toHaveLength(5);
    expect(screen.getByRole("tab", { name: i18n.t("Researcher Settings Tab") })).toBeInTheDocument();
  });
});
