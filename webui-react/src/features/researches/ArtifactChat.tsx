import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  ARTIFACT_FIELDS,
  getArtifactRestoreParams,
  postArtifactChat,
  type ArtifactChatMessage,
  type ArtifactField,
  type ResearchArtifact,
} from "@/api/research";
import { useGenerationStore } from "@/store/generationStore";
import type { VideoParams } from "@/types/videoParams";

const OPTIONAL_FIELDS = ARTIFACT_FIELDS.filter((field): field is Exclude<ArtifactField, "video_subject"> => field !== "video_subject");

const FIELD_LABEL_KEYS: Record<ArtifactField, string> = {
  video_subject: "Video Subject",
  video_script_prompt: "Custom Script Requirements",
  custom_system_prompt: "Custom System Prompt",
  video_script: "Video Script",
  video_terms: "Video Keywords",
};

type Stage = "idle" | "selecting" | "chatting" | "done";

export function ArtifactChat({ researchId, entity, clusterId, artifact }: {
  researchId: string;
  entity: string;
  clusterId: string;
  artifact?: ResearchArtifact;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [stage, setStage] = useState<Stage>("idle");
  const [selectedFields, setSelectedFields] = useState<ArtifactField[]>(
    artifact ? ["video_subject", ...artifact.generated_fields] : ["video_subject"],
  );
  const [messages, setMessages] = useState<ArtifactChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const chat = useMutation({
    mutationFn: (nextMessages: ArtifactChatMessage[]) =>
      postArtifactChat(researchId, entity, clusterId, selectedFields, nextMessages),
    onSuccess: (turn, nextMessages) => {
      if (turn.type === "question") {
        setMessages([...nextMessages, { role: "assistant", content: turn.message }]);
        setStage("chatting");
        return;
      }
      setSavedMessage(turn.message);
      setStage("done");
      void queryClient.invalidateQueries({ queryKey: ["research", researchId] });
    },
  });

  const restore = useMutation({
    mutationFn: () => getArtifactRestoreParams(researchId, entity, clusterId),
    onSuccess: ({ params }) => {
      useGenerationStore.getState().loadParams(params as unknown as VideoParams);
      navigate("/generate");
    },
  });

  function toggleField(field: ArtifactField) {
    setSelectedFields((current) => (current.includes(field) ? current.filter((item) => item !== field) : [...current, field]));
  }

  function startChat() {
    setMessages([]);
    chat.mutate([]);
  }

  function sendReply() {
    const content = draft.trim();
    if (!content) return;
    setDraft("");
    chat.mutate([...messages, { role: "user", content }]);
  }

  function closeDialog() {
    setStage("idle");
    setMessages([]);
    setDraft("");
    setSavedMessage(null);
  }

  return <div className="space-y-2">
    {artifact && stage === "idle" ? <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
      <p className="text-sm font-medium">{t("Generated artifacts")}</p>
      <dl className="space-y-1 text-sm">
        <div><dt className="inline font-medium">{t(FIELD_LABEL_KEYS.video_subject)}: </dt><dd className="inline text-muted-foreground">{artifact.video_subject}</dd></div>
        {OPTIONAL_FIELDS.filter((field) => artifact.generated_fields.includes(field)).map((field) => <div key={field}>
          <dt className="inline font-medium">{t(FIELD_LABEL_KEYS[field])}: </dt>
          <dd className="inline whitespace-pre-wrap text-muted-foreground">
            {field === "video_terms" ? (artifact.video_terms ?? []).join(", ") : artifact[field]}
          </dd>
        </div>)}
      </dl>
      <div className="flex gap-2">
        <Button type="button" variant="primary" disabled={restore.isPending} onClick={() => restore.mutate()}>{t("Use artifacts")}</Button>
        <Button type="button" onClick={() => setStage("selecting")}>{t("Generate again")}</Button>
      </div>
      {restore.error ? <p role="alert" className="text-sm text-destructive">{restore.error.message}</p> : null}
    </div> : null}

    {!artifact && stage === "idle" ? <Button type="button" onClick={() => setStage("selecting")}>{t("Generate artifacts")}</Button> : null}

    <Dialog open={stage === "selecting"} onClose={closeDialog} title={t("Generate artifacts")}>
      <div className="space-y-4">
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t("Choose fields to generate")}</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked disabled aria-label={t(FIELD_LABEL_KEYS.video_subject)} />
            <span>{t(FIELD_LABEL_KEYS.video_subject)}</span>
          </label>
          {OPTIONAL_FIELDS.map((field) => <label key={field} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              aria-label={t(FIELD_LABEL_KEYS[field])}
              checked={selectedFields.includes(field)}
              onChange={() => toggleField(field)}
            />
            <span>{t(FIELD_LABEL_KEYS[field])}</span>
          </label>)}
        </fieldset>
        {chat.error ? <p role="alert" className="text-sm text-destructive">{chat.error.message}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={closeDialog}>{t("Cancel")}</Button>
          <Button type="button" variant="primary" disabled={chat.isPending} onClick={startChat}>{t("Continue")}</Button>
        </div>
      </div>
    </Dialog>

    <Dialog open={stage === "chatting" || stage === "done"} onClose={closeDialog} title={t("Generate artifacts")}>
      <div className="space-y-4">
        <div className="max-h-80 space-y-2 overflow-y-auto">
          {messages.map((message, index) => <p key={index} className={message.role === "user" ? "text-right text-sm" : "text-sm text-muted-foreground"}>
            <span className="font-medium">{message.role === "user" ? t("You") : t("Agent")}: </span>{message.content}
          </p>)}
        </div>
        {stage === "done"
          ? <p role="status" className="text-sm text-primary">{savedMessage}</p>
          : <>
            <Textarea aria-label={t("Your reply")} value={draft} onChange={(event) => setDraft(event.target.value)} rows={3} />
            {chat.error ? <p role="alert" className="text-sm text-destructive">{chat.error.message}</p> : null}
            <div className="flex justify-end gap-2">
              <Button type="button" onClick={closeDialog}>{t("Cancel")}</Button>
              <Button type="button" variant="primary" disabled={chat.isPending || !draft.trim()} onClick={sendReply}>{t("Send")}</Button>
            </div>
          </>}
        {stage === "done" ? <div className="flex justify-end"><Button type="button" onClick={closeDialog}>{t("Close")}</Button></div> : null}
      </div>
    </Dialog>
  </div>;
}
