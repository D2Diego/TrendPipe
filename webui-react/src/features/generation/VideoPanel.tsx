import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Field, Select } from "@/components/ui/field";
import { getUiConfig, setUiConfigValue } from "@/api/config";
import { useGenerationStore } from "@/store/generationStore";
import { Panel } from "./Panel";

const sources = [["Pexels", "pexels"], ["Pixabay", "pixabay"], ["Coverr", "coverr"], ["Local file", "local"]] as const;
const transitions = [["None", ""], ["Shuffle", "Shuffle"], ["FadeIn", "FadeIn"], ["FadeOut", "FadeOut"], ["SlideIn", "SlideIn"], ["SlideOut", "SlideOut"], ["ZoomIn", "ZoomIn"], ["ZoomOut", "ZoomOut"]] as const;
const codecs = [["Default Video Encoder", "default"], ["libx264 (CPU)", "libx264"], ["NVIDIA NVENC (h264_nvenc)", "h264_nvenc"], ["AMD AMF (h264_amf)", "h264_amf"], ["Intel QSV (h264_qsv)", "h264_qsv"], ["Windows MediaFoundation (h264_mf)", "h264_mf"], ["macOS VideoToolbox (h264_videotoolbox)", "h264_videotoolbox"]] as const;

export function VideoPanel() {
  const { t } = useTranslation();
  const params = useGenerationStore((state) => state.params);
  const setParam = useGenerationStore((state) => state.setParam);
  const setFiles = useGenerationStore((state) => state.setLocalFilesToUpload);
  const videoCodec = useGenerationStore((state) => state.videoCodec);
  const setVideoCodec = useGenerationStore((state) => state.setVideoCodec);
  const previousConcat = useRef<"random" | "sequential">("random");
  const [aspects, setAspects] = useState<Record<string, "9:16" | "16:9">>({ coverr: "16:9" });
  const uiConfig = useQuery({ queryKey: ["ui-config"], queryFn: getUiConfig, staleTime: 30_000 });
  const codecHydrated = useRef(false);
  useEffect(() => {
    if (codecHydrated.current || !uiConfig.data) return;
    codecHydrated.current = true;
    if (typeof uiConfig.data.video_codec === "string") setVideoCodec(uiConfig.data.video_codec);
  }, [setVideoCodec, uiConfig.data]);

  const setSource = (source: string) => {
    setParam("video_source", source);
    setParam("video_aspect", aspects[source] || (source === "coverr" ? "16:9" : "9:16"));
  };
  const toggleMatch = (checked: boolean) => {
    if (checked) {
      previousConcat.current = params.video_concat_mode;
      setParam("video_concat_mode", "sequential");
    } else setParam("video_concat_mode", previousConcat.current);
    setParam("match_materials_to_script", checked);
  };

  return <Panel title={t("Video Settings")}>
    <Field label={t("Video Source")} htmlFor="video-source">
      <Select id="video-source" aria-label={t("Video Source")} value={params.video_source} onChange={(event) => setSource(event.target.value)}>
        {sources.map(([label, value]) => <option key={value} value={value}>{t(label)}</option>)}
      </Select>
    </Field>
    {params.video_source === "local" ? <Field label={t("Upload Local Files")} htmlFor="local-files"><input id="local-files" aria-label={t("Upload Local Files")} className="block w-full text-sm" type="file" accept="video/*,.mp4,.mov,.avi,.mkv,.webm" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} /></Field> : null}
    <Field label={t("Video Concat Mode")} htmlFor="concat-mode">
      <Select id="concat-mode" aria-label={t("Video Concat Mode")} disabled={params.match_materials_to_script} value={params.video_concat_mode} onChange={(event) => setParam("video_concat_mode", event.target.value as "random" | "sequential")}>
        <option value="sequential">{t("Sequential")}</option><option value="random">{t("Random")}</option>
      </Select>
    </Field>
    <label className="flex items-start gap-2"><input aria-label={t("Match Materials to Script Order")} type="checkbox" checked={params.match_materials_to_script} onChange={(event) => toggleMatch(event.target.checked)} /><span>{t("Match Materials to Script Order")}<small className="block font-normal text-muted-foreground">{t("Match Materials to Script Order Help")}</small></span></label>
    <Field label={t("Video Transition Mode")} htmlFor="transition-mode"><Select id="transition-mode" aria-label={t("Video Transition Mode")} value={params.video_transition_mode || ""} onChange={(event) => setParam("video_transition_mode", event.target.value || null)}>{transitions.map(([label, value]) => <option key={label} value={value}>{t(label)}</option>)}</Select></Field>
    <Field label={t("Video Ratio")} htmlFor="video-ratio"><Select id="video-ratio" aria-label={t("Video Ratio")} value={params.video_aspect} onChange={(event) => { const value = event.target.value as "9:16" | "16:9"; setParam("video_aspect", value); setAspects((current) => ({ ...current, [params.video_source]: value })); }}><option value="9:16">{t("Portrait")}</option><option value="16:9">{t("Landscape")}</option></Select></Field>
    <Field label={t("Clip Duration")} htmlFor="clip-duration" help={t("Clip Duration Help")}><Select id="clip-duration" value={params.video_clip_duration} onChange={(event) => setParam("video_clip_duration", Number(event.target.value))}>{Array.from({ length: 9 }, (_, i) => i + 2).map((value) => <option key={value}>{value}</option>)}</Select></Field>
    <Field label={`${t("Clip Speed")}: ${params.video_clip_speed.toFixed(2)}×`} htmlFor="clip-speed" help={t("Clip Speed Help")}><input id="clip-speed" className="w-full accent-primary" type="range" min="0.5" max="2" step="0.05" value={params.video_clip_speed} onChange={(event) => setParam("video_clip_speed", Number(event.target.value))} /></Field>
    <Field label={t("Number of Videos Generated Simultaneously")} htmlFor="video-count"><Select id="video-count" value={params.video_count} onChange={(event) => setParam("video_count", Number(event.target.value))}>{[1, 2, 3, 4, 5].map((value) => <option key={value}>{value}</option>)}</Select></Field>
    <Field label={t("Video Encoder")} htmlFor="video-codec" help={t("Video Encoder Help")}><Select id="video-codec" value={videoCodec} onChange={(event) => { setVideoCodec(event.target.value); void setUiConfigValue("video_codec", event.target.value); }}>{codecs.map(([label, value]) => <option key={value} value={value}>{label.startsWith("Default") ? t(label) : label}</option>)}</Select></Field>
  </Panel>;
}
