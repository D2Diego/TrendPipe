import { describe, expect, it } from "vitest";
import { formatTaskSubject, formatTaskTime, taskStatusFilterKey } from "./format";

describe("task formatters", () => {
  it("formats time and subjects", () => {
    expect(formatTaskTime(undefined)).toBe("-");
    expect(formatTaskTime(1700000000)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
    expect(formatTaskSubject("a\nb")).toBe("a b");
    expect(formatTaskSubject("x".repeat(50))).toBe(`${"x".repeat(30)}...`);
  });
  it("maps real backend states", () => {
    expect(taskStatusFilterKey({ state: 4 })).toBe("processing");
    expect(taskStatusFilterKey({ state: -1 })).toBe("failed");
    expect(taskStatusFilterKey({ state: 1 })).toBe("complete");
    expect(taskStatusFilterKey({ state: null, video_file: "x" })).toBe("complete");
    expect(taskStatusFilterKey({ state: null })).toBe("history");
  });
});
