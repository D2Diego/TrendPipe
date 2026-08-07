import { beforeAll, describe, expect, it } from "vitest";
import i18n from "./index";

describe("i18n", () => {
  beforeAll(() => i18n.changeLanguage("en"));
  it("loads existing translations", () => expect(i18n.t("Generate Video")).toBe("Generate Video"));
  it("falls back to unknown keys", () => expect(i18n.t("Unknown Test Key")).toBe("Unknown Test Key"));
  it("supports the existing single-brace placeholders", () => {
    i18n.addResource("en", "translation", "Placeholder Test", "Hello {name}");
    expect(i18n.t("Placeholder Test", { name: "World" })).toBe("Hello World");
  });
  it("treats dotted keys as flat literal keys", () => {
    i18n.addResource("en", "translation", "llm_provider_tips.example_provider", "Example tip text");
    expect(i18n.t("llm_provider_tips.example_provider")).toBe("Example tip text");
  });
});
