import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import * as scriptsApi from "@/api/scripts";
import { useGenerationStore } from "@/store/generationStore";
import { ScriptPanel } from "./ScriptPanel";

describe("ScriptPanel", () => {
  beforeEach(() => { void i18n.changeLanguage("en"); useGenerationStore.getState().reset(); });
  it("binds subject and paragraph count to generation state", () => {
    render(<QueryClientProvider client={new QueryClient()}><ScriptPanel /></QueryClientProvider>);
    fireEvent.change(screen.getByLabelText(i18n.t("Video Subject")), { target: { value: "cats in space" } });
    fireEvent.change(screen.getByLabelText(i18n.t("Script Paragraph Number")), { target: { value: "4" } });
    expect(useGenerationStore.getState().params).toEqual(expect.objectContaining({ video_subject: "cats in space", paragraph_number: 4 }));
    expect(screen.getByRole("button", { name: i18n.t("Generate Video Keywords") })).toBeDisabled();
  });
  it("offers Brazilian Portuguese as an explicit script language", () => {
    render(<QueryClientProvider client={new QueryClient()}><ScriptPanel /></QueryClientProvider>);
    expect(screen.getByRole("option", { name: "pt-BR" })).toBeInTheDocument();
  });
  it("previews the exact prompt returned by the backend", async () => {
    vi.spyOn(scriptsApi, "previewScriptPrompt").mockResolvedValue({ prompt: "exact final prompt" });
    render(<QueryClientProvider client={new QueryClient()}><ScriptPanel /></QueryClientProvider>);
    fireEvent.click(screen.getByText(i18n.t("Advanced Script Settings")));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Preview Final Prompt") }));
    expect(await screen.findByText("exact final prompt")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: i18n.t("Final Prompt Preview") })).toBeInTheDocument();
  });
});
