export interface DurationRange { min: number; max: number }

export function estimateVoiceoverDurationRange(text: string, voiceRate: number): DurationRange | null {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (!normalized) return null;
  const scriptChars = normalized.match(/[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]/g) || [];
  const remaining = normalized.replace(/[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]/g, " ");
  const words = remaining.match(/\b[\p{L}\p{N}_]+(?:[-'’][\p{L}\p{N}_]+)*\b/gu) || [];
  const punctuation = normalized.match(/[,，.。!?！？;；:：]/g) || [];
  const baseSeconds = scriptChars.length / 4.2 + words.length / 2.6 + punctuation.length * 0.12;
  if (baseSeconds <= 0) return null;
  const seconds = baseSeconds / Math.max(Number(voiceRate) || 1, 0.1);
  return { min: Math.round(Math.max(seconds * 0.85, 1) * 10) / 10, max: Math.round(Math.max(seconds * 1.15, 1) * 10) / 10 };
}
