import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LocalAudioPreview } from "./LocalAudioPreview";

describe("LocalAudioPreview", () => {
  afterEach(() => {
    Reflect.deleteProperty(URL, "createObjectURL");
    Reflect.deleteProperty(URL, "revokeObjectURL");
  });
  it("creates and revokes a browser URL for an uploaded audio file", () => {
    const create = vi.fn(() => "blob:preview");
    const revoke = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
    const view = render(<LocalAudioPreview file={new File(["audio"], "sample.mp3", { type: "audio/mpeg" })} label="Audio preview" />);
    expect(screen.getByLabelText("Audio preview")).toHaveAttribute("src", "blob:preview");
    expect(create).toHaveBeenCalledOnce();
    view.unmount();
    expect(revoke).toHaveBeenCalledWith("blob:preview");
  });
});
