import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CredentialRow } from "./CredentialRow";
import * as researchApi from "@/api/research";
import i18n from "@/i18n";

function renderRow(props: Partial<React.ComponentProps<typeof CredentialRow>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CredentialRow credKey="OPENROUTER_API_KEY" present={false} {...props} />
    </QueryClientProvider>,
  );
}

describe("CredentialRow", () => {
  beforeEach(() => { void i18n.changeLanguage("en"); });
  afterEach(() => vi.restoreAllMocks());

  it("shows an always-visible input and Save when not configured", async () => {
    const saveMock = vi.spyOn(researchApi, "updateResearchSettings").mockResolvedValue({ saved: true });
    renderRow({ present: false });

    expect(screen.getByText(/missing/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("OPENROUTER_API_KEY"), "sk-or-abc");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(saveMock).toHaveBeenCalledWith({ OPENROUTER_API_KEY: "sk-or-abc" }));
    expect(await screen.findByText("OPENROUTER_API_KEY updated.")).toBeInTheDocument();
    expect(screen.queryByLabelText("OPENROUTER_API_KEY")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /change/i })).toBeInTheDocument();
  });

  it("shows Change/Delete when configured, and Change reveals an edit form", async () => {
    renderRow({ present: true });

    expect(screen.getByText(/configured/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("OPENROUTER_API_KEY")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /change/i }));
    expect(screen.getByLabelText("OPENROUTER_API_KEY")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByLabelText("OPENROUTER_API_KEY")).not.toBeInTheDocument();
  });

  it("deletes only after confirming in the dialog", async () => {
    const deleteMock = vi.spyOn(researchApi, "deleteResearchCredential").mockResolvedValue({ deleted: true });
    renderRow({ present: true });

    await userEvent.click(screen.getByRole("button", { name: /delete openrouter_api_key/i }));
    expect(screen.getByRole("dialog", { name: /remove credential/i })).toBeInTheDocument();
    expect(deleteMock).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /^remove$/i }));

    await waitFor(() => expect(deleteMock).toHaveBeenCalledWith("OPENROUTER_API_KEY"));
    expect(await screen.findByText("OPENROUTER_API_KEY removed.")).toBeInTheDocument();
    expect(screen.getByLabelText("OPENROUTER_API_KEY")).toBeInTheDocument();
    expect(screen.getByText(/missing/i)).toBeInTheDocument();
  });

  it("does not delete when the dialog is canceled", async () => {
    const deleteMock = vi.spyOn(researchApi, "deleteResearchCredential").mockResolvedValue({ deleted: true });
    renderRow({ present: true });

    await userEvent.click(screen.getByRole("button", { name: /delete openrouter_api_key/i }));
    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteMock).not.toHaveBeenCalled();
  });
});
