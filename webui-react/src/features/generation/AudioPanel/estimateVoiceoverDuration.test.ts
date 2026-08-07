import { describe, expect, it } from "vitest";
import { estimateVoiceoverDurationRange } from "./estimateVoiceoverDuration";

describe("estimateVoiceoverDurationRange", () => {
  it("uses the voiceover heuristic and scales inversely with rate", () => {
    expect(estimateVoiceoverDurationRange("", 1)).toBeNull();
    const slow = estimateVoiceoverDurationRange("Hello, world! This is a test.", 1)!;
    const fast = estimateVoiceoverDurationRange("Hello, world! This is a test.", 2)!;
    expect(fast.max).toBeLessThan(slow.max);
  });
});
