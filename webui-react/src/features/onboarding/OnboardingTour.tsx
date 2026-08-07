import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export const ONBOARDING_STORAGE_KEY = "mpt-onboarding-v1";

const steps = [
  { target: "[data-tour-id='settings']", title: "Onboarding Model Settings Title", description: "Onboarding Model Settings Description" },
  { target: "[data-tour-id='main-settings-grid']", title: "Onboarding Creation Settings Title", description: "Onboarding Creation Settings Description" },
  { target: "[data-tour-id='generate-video']", title: "Onboarding Generate Video Title", description: "Onboarding Generate Video Description" },
];

export function OnboardingTour() {
  const { t } = useTranslation();
  const [step, setStep] = useState(() => localStorage.getItem(ONBOARDING_STORAGE_KEY) ? -1 : 0);

  useEffect(() => {
    if (step < 0) return;
    const target = document.querySelector<HTMLElement>(steps[step].target);
    if (!target) return;
    const previousPosition = target.style.position;
    const previousZIndex = target.style.zIndex;
    target.style.position = previousPosition || "relative";
    target.style.zIndex = "45";
    target.scrollIntoView?.({ behavior: "smooth", block: "center" });
    return () => {
      target.style.position = previousPosition;
      target.style.zIndex = previousZIndex;
    };
  }, [step]);

  if (step < 0) return null;
  const current = steps[step];
  const finish = () => {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, "complete");
    setStep(-1);
  };

  return <div className="fixed inset-0 z-40 bg-background/60" data-testid="onboarding-tour">
    <section role="dialog" aria-label={t(current.title)} className="fixed bottom-6 left-1/2 z-50 w-[min(92vw,30rem)] -translate-x-1/2 rounded-lg border border-border bg-card p-5 text-card-foreground shadow-lg">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div><p className="text-xs text-muted-foreground">{step + 1} / {steps.length}</p><h2 className="font-semibold">{t(current.title)}</h2></div>
        <button type="button" aria-label="Close" className="rounded p-1 text-muted-foreground hover:bg-accent" onClick={finish}>✕</button>
      </div>
      <p className="text-sm text-muted-foreground">{t(current.description)}</p>
      <div className="mt-4 flex justify-end gap-2">
        {step > 0 ? <Button type="button" onClick={() => setStep((value) => value - 1)}>{t("Onboarding Previous")}</Button> : null}
        {step < steps.length - 1
          ? <Button variant="primary" type="button" onClick={() => setStep((value) => value + 1)}>{t("Onboarding Next")}</Button>
          : <Button variant="primary" type="button" onClick={finish}>{t("Onboarding Done")}</Button>}
      </div>
    </section>
  </div>;
}
