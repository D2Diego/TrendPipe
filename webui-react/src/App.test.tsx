import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./App";
import App from "./App";

describe("App", () => {
  it("renders the workflow choice at the root route", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /how do you want to start|como você quer começar/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /develop an idea with research|desenvolver uma ideia com pesquisa/i })).toHaveAttribute("href", "/researches");
    expect(screen.getByRole("link", { name: /already have an idea|já tenho uma ideia/i })).toHaveAttribute("href", "/generate");
  });

  it("renders the responsive generation grid at /generate", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={["/generate"]}><AppRoutes /></MemoryRouter></QueryClientProvider>);
    expect(screen.getByTestId("main-settings-grid")).toBeInTheDocument();
  });

  it("renders the research list page at /researches", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={["/researches"]}><AppRoutes /></MemoryRouter></QueryClientProvider>);
    expect(screen.getByTestId("research-list-page")).toBeInTheDocument();
  });

  it("redirects the legacy credentials page into researcher settings", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={["/researches/settings"]}><AppRoutes /></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByTestId("researcher-settings-tab")).toBeInTheDocument();
  });
});
