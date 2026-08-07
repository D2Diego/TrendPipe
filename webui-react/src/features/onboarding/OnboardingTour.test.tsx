import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import i18n from "@/i18n";
import { OnboardingTour, ONBOARDING_STORAGE_KEY } from "./OnboardingTour";

describe("OnboardingTour", () => {
  beforeEach(() => { localStorage.clear(); void i18n.changeLanguage("en"); });

  it("guides the three stable entry points once", () => {
    render(<><button data-tour-id="settings" /><div data-tour-id="main-settings-grid" /><button data-tour-id="generate-video" /><OnboardingTour /></>);
    expect(screen.getByRole("dialog", { name: i18n.t("Onboarding Model Settings Title") })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Onboarding Next") }));
    expect(screen.getByRole("dialog", { name: i18n.t("Onboarding Creation Settings Title") })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Onboarding Next") }));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("Onboarding Done") }));
    expect(screen.queryByTestId("onboarding-tour")).not.toBeInTheDocument();
    expect(localStorage.getItem(ONBOARDING_STORAGE_KEY)).toBe("complete");
  });

  it("stays dismissed after completion", () => {
    localStorage.setItem(ONBOARDING_STORAGE_KEY, "complete");
    render(<OnboardingTour />);
    expect(screen.queryByTestId("onboarding-tour")).not.toBeInTheDocument();
  });
});
