import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import i18n from "@/i18n";
import { AudioPanel } from "@/features/generation/AudioPanel";
import { GenerationControls } from "@/features/generation/GenerationControls";
import { ScriptPanel } from "@/features/generation/ScriptPanel";
import { SubtitlePanel } from "@/features/generation/SubtitlePanel";
import { TopBar } from "@/features/generation/TopBar";
import { VideoPanel } from "@/features/generation/VideoPanel";
import { OnboardingTour } from "@/features/onboarding/OnboardingTour";
import { ResearchListPage } from "@/features/researches/ResearchListPage";
import { ResearchDetailPage } from "@/features/researches/ResearchDetailPage";
import { StartPage } from "@/features/start/StartPage";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function GenerationScreen() {
  return <>
    <div data-testid="main-settings-grid" data-tour-id="main-settings-grid" className="grid grid-cols-1 items-start gap-4 p-4 min-[701px]:grid-cols-2 min-[1101px]:grid-cols-4">
      <ScriptPanel /><VideoPanel /><AudioPanel /><SubtitlePanel />
    </div>
    <GenerationControls />
    <OnboardingTour />
  </>;
}

export function AppRoutes() {
  return <>
    <TopBar />
    <Routes>
      <Route path="/" element={<StartPage />} />
      <Route path="/generate" element={<GenerationScreen />} />
      <Route path="/researches" element={<ResearchListPage />} />
      <Route path="/researches/settings" element={<Navigate to="/researches?settings=researcher" replace />} />
      <Route path="/researches/:id" element={<ResearchDetailPage />} />
    </Routes>
  </>;
}

export default function App() {
  return <QueryClientProvider client={queryClient}><I18nextProvider i18n={i18n}>
    <main className="min-h-screen bg-background text-foreground">
      <BrowserRouter><AppRoutes /></BrowserRouter>
    </main>
  </I18nextProvider></QueryClientProvider>;
}
