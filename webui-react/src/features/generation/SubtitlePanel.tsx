import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { checkFontSupport, listFonts } from "@/api/fonts";
import { getUiConfig, setUiConfigValue } from "@/api/config";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { DEFAULT_VIDEO_PARAMS } from "@/types/videoParams";
import { useGenerationStore } from "@/store/generationStore";
import { Panel } from "./Panel";

export function SubtitlePanel() {
  const { t } = useTranslation();
  const params = useGenerationStore((state) => state.params);
  const setParam = useGenerationStore((state) => state.setParam);
  const fonts = useQuery({ queryKey: ["fonts"], queryFn: listFonts, staleTime: 30_000 });
  const uiConfig = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, staleTime: 30_000 });
  const [backgroundColor, setBackgroundColor] = useState("#000000");
  const [backgroundEnabled, setBackgroundEnabled] = useState(false);
  const [roundedPreferred, setRoundedPreferred] = useState(false);
  const hydrated = useRef(false);
  useEffect(() => {
    if (hydrated.current || !uiConfig.data) return;
    hydrated.current = true;
    const saved = uiConfig.data;
    if (typeof saved.font_name === "string") setParam("font_name", saved.font_name);
    if (["top", "center", "bottom", "custom"].includes(String(saved.subtitle_position))) setParam("subtitle_position", String(saved.subtitle_position));
    if (typeof saved.custom_position === "number") setParam("custom_position", saved.custom_position);
    if (typeof saved.text_fore_color === "string") setParam("text_fore_color", saved.text_fore_color);
    if (typeof saved.font_size === "number") setParam("font_size", saved.font_size);
    const color = typeof saved.subtitle_background_color === "string" ? saved.subtitle_background_color : "#000000";
    const enabled = saved.subtitle_background_enabled === true;
    const rounded = saved.rounded_subtitle_background === true;
    setBackgroundColor(color); setBackgroundEnabled(enabled); setRoundedPreferred(rounded);
    setParam("text_background_color", enabled ? color : false);
    setParam("rounded_subtitle_background", enabled && rounded);
  }, [setParam, uiConfig.data]);
  const previewText = params.video_script || params.video_subject;
  const fontSupport = useQuery({
    queryKey: ["font-support", params.font_name, previewText],
    queryFn: () => checkFontSupport(params.font_name, previewText),
    enabled: params.subtitle_enabled && Boolean(params.font_name && previewText),
    staleTime: 30_000,
  });
  const disabled = !params.subtitle_enabled;
  const invalidCustom = params.subtitle_position === "custom" && (!Number.isFinite(params.custom_position) || params.custom_position < 0 || params.custom_position > 100);
  const restore = () => {
    (["subtitle_enabled", "font_name", "subtitle_position", "custom_position", "text_fore_color", "font_size", "stroke_color", "stroke_width", "text_background_color", "rounded_subtitle_background"] as const).forEach((key) => setParam(key, DEFAULT_VIDEO_PARAMS[key]));
    setBackgroundColor("#000000"); setBackgroundEnabled(false); setRoundedPreferred(false);
    void (async () => {
      for (const [key, value] of Object.entries({ font_name: DEFAULT_VIDEO_PARAMS.font_name, subtitle_position: DEFAULT_VIDEO_PARAMS.subtitle_position, custom_position: DEFAULT_VIDEO_PARAMS.custom_position, text_fore_color: DEFAULT_VIDEO_PARAMS.text_fore_color, font_size: DEFAULT_VIDEO_PARAMS.font_size, subtitle_background_enabled: false, subtitle_background_color: "#000000", rounded_subtitle_background: false })) await setUiConfigValue(key, value);
    })();
  };

  return <Panel title={t("Subtitle Settings")}>
    <label className="flex items-center gap-2"><input type="checkbox" aria-label={t("Enable Subtitles")} checked={params.subtitle_enabled} onChange={(event) => setParam("subtitle_enabled", event.target.checked)} />{t("Enable Subtitles")}</label>
    <Field label={t("Font")} htmlFor="font"><Select id="font" aria-label={t("Font")} disabled={disabled || fonts.isLoading} value={params.font_name} onChange={(event) => { setParam("font_name", event.target.value); void setUiConfigValue("font_name", event.target.value); }}>{(fonts.data?.fonts || [params.font_name]).map((font) => <option key={font}>{font}</option>)}</Select></Field>
    <Field label={t("Position")} htmlFor="subtitle-position"><Select id="subtitle-position" aria-label={t("Position")} disabled={disabled} value={params.subtitle_position} onChange={(event) => { setParam("subtitle_position", event.target.value); void setUiConfigValue("subtitle_position", event.target.value); }}><option value="top">{t("Top")}</option><option value="center">{t("Center")}</option><option value="bottom">{t("Bottom")}</option><option value="custom">{t("Custom")}</option></Select></Field>
    {params.subtitle_position === "custom" ? <Field label={t("Custom Position (% from top)")} htmlFor="custom-position"><Input id="custom-position" aria-label={t("Custom Position (% from top)")} disabled={disabled} inputMode="decimal" value={Number.isNaN(params.custom_position) ? "" : params.custom_position} onChange={(event) => { const value = event.target.value === "" ? Number.NaN : Number(event.target.value); setParam("custom_position", value); if (Number.isFinite(value) && value >= 0 && value <= 100) void setUiConfigValue("custom_position", value); }} />{invalidCustom ? <p role="alert" className="mt-1 text-sm text-destructive-foreground">{Number.isNaN(params.custom_position) ? t("Please enter a valid number") : t("Please enter a value between 0 and 100")}</p> : null}</Field> : null}
    <div className="grid grid-cols-[0.42fr_0.58fr] gap-3"><Field label={t("Font Color")} htmlFor="font-color"><Input id="font-color" type="color" disabled={disabled} value={params.text_fore_color} onChange={(event) => { const value = event.target.value.toUpperCase(); setParam("text_fore_color", value); void setUiConfigValue("text_fore_color", value); }} /></Field><Field label={`${t("Font Size")}: ${params.font_size}`} htmlFor="font-size"><input id="font-size" className="w-full accent-primary" type="range" min="30" max="100" disabled={disabled} value={params.font_size} onChange={(event) => { const value = Number(event.target.value); setParam("font_size", value); void setUiConfigValue("font_size", value); }} /></Field></div>
    <div className="grid grid-cols-[0.42fr_0.58fr] gap-3"><Field label={t("Stroke Color")} htmlFor="stroke-color"><Input id="stroke-color" type="color" disabled={disabled} value={params.stroke_color} onChange={(event) => setParam("stroke_color", event.target.value.toUpperCase())} /></Field><Field label={`${t("Stroke Width")}: ${params.stroke_width.toFixed(1)}`} htmlFor="stroke-width"><input id="stroke-width" className="w-full accent-primary" type="range" min="0" max="10" step="0.5" disabled={disabled} value={params.stroke_width} onChange={(event) => setParam("stroke_width", Number(event.target.value))} /></Field></div>
    <div className="grid grid-cols-[0.55fr_0.45fr] items-end gap-3"><label className="flex items-center gap-2"><input type="checkbox" disabled={disabled} checked={backgroundEnabled} onChange={(event) => { const enabled = event.target.checked; setBackgroundEnabled(enabled); setParam("text_background_color", enabled ? backgroundColor : false); setParam("rounded_subtitle_background", enabled && roundedPreferred); void setUiConfigValue("subtitle_background_enabled", enabled); }} />{t("Enable Subtitle Background")}</label><Field label={t("Subtitle Background Color")} htmlFor="background-color"><Input id="background-color" type="color" disabled={disabled || !backgroundEnabled} value={backgroundColor} onChange={(event) => { const color = event.target.value.toUpperCase(); setBackgroundColor(color); setParam("text_background_color", color); void setUiConfigValue("subtitle_background_color", color); }} /></Field></div>
    <label className="flex items-start gap-2"><input type="checkbox" disabled={disabled || !backgroundEnabled} checked={roundedPreferred} onChange={(event) => { setRoundedPreferred(event.target.checked); setParam("rounded_subtitle_background", event.target.checked); void setUiConfigValue("rounded_subtitle_background", event.target.checked); }} /><span>{t("Rounded Subtitle Background")}<small className="block font-normal text-muted-foreground">{t("Rounded Subtitle Background Help")}</small></span></label>
    {backgroundEnabled && params.text_fore_color.toLowerCase() === backgroundColor.toLowerCase() ? <p className="text-sm text-warning">{t("Subtitle Colors Are Indistinguishable")}</p> : null}
    {fontSupport.data?.supported === false ? <p className="text-sm text-warning">{t("Subtitle Font Does Not Support Text")}</p> : null}
    <Button type="button" className="w-full" onClick={restore}>{t("Restore Default Subtitle Settings")}</Button>
  </Panel>;
}
