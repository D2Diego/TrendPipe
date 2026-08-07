import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NewResearchForm } from "./NewResearchForm";
import * as researchApi from "@/api/research";

function renderForm(onCreated = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}><MemoryRouter><NewResearchForm onCreated={onCreated} /></MemoryRouter></QueryClientProvider>);
  return onCreated;
}

describe("NewResearchForm", () => {
  afterEach(() => vi.restoreAllMocks());

  it("enables only currently available sources", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: ["reddit"] });
    renderForm();

    await waitFor(() => expect(screen.getByLabelText(/^reddit$/i)).toBeEnabled());
    expect(screen.getByLabelText(/^hackernews$/i)).toBeDisabled();
    expect(screen.queryByRole("link", { name: /credentials|credenciais/i })).not.toBeInTheDocument();
    expect(screen.getByText(/settings.*researcher|ajustes.*pesquisador/i)).toBeInTheDocument();
  });

  it("submits topic, depth, and selected sources", async () => {
    vi.spyOn(researchApi, "getResearchSettings").mockResolvedValue({ available_sources: ["reddit"] });
    const createMock = vi.spyOn(researchApi, "createResearch").mockResolvedValue({
      id: "r1", topic: "cats", status: "pending", depth: "quick", sources: ["reddit"],
      error_message: null, report_json: null, created_at: "", updated_at: "",
    });
    const onCreated = renderForm();

    await waitFor(() => expect(screen.getByLabelText(/^reddit$/i)).toBeEnabled());
    await userEvent.type(screen.getByLabelText(/research topic|tema da pesquisa/i), " cats ");
    await userEvent.click(screen.getByLabelText(/^reddit$/i));
    await userEvent.click(screen.getByRole("button", { name: /search|pesquisar/i }));

    await waitFor(() => expect(createMock).toHaveBeenCalledWith({ topic: "cats", depth: "quick", sources: ["reddit"] }));
    expect(onCreated).toHaveBeenCalledWith("r1");
  });
});
