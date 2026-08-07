import { apiGet, apiPost } from "./client";
export const listFonts = () => apiGet<{ fonts: string[] }>("/fonts");
export const checkFontSupport = (font_name: string, text: string) => apiPost<{ supported: boolean }>("/fonts/support", { font_name, text });
