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

type Stage = "idle" | "selecting" | "chatting";

function DraftSummary({ draft, onUse, useIsPending }: { draft: ResearchArtifact; onUse: () => void; useIsPending: boolean }) {
  const { t } = useTranslation();
  return <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
    <p className="text-sm font-medium">{t("Generated artifacts")}</p>
    <dl className="space-y-1 text-sm">
      <div><dt className="inline font-medium">{t(FIELD_LABEL_KEYS.video_subject)}: </dt><dd className="inline text-muted-foreground">{draft.video_subject}</dd></div>
      {OPTIONAL_FIELDS.filter((field) => draft.generated_fields.includes(field)).map((field) => <div key={field}>
        <dt className="inline font-medium">{t(FIELD_LABEL_KEYS[field])}: </dt>
        <dd className="inline whitespace-pre-wrap text-muted-foreground">
          {field === "video_terms" ? (draft.video_terms ?? []).join(", ") : draft[field]}
        </dd>
      </div>)}
    </dl>
    <Button type="button" variant="primary" disabled={useIsPending} onClick={onUse}>{t("Use artifacts")}</Button>
  </div>;
}

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
  const [replyDraft, setReplyDraft] = useState("");
  const [currentDraft, setCurrentDraft] = useState<ResearchArtifact | null>(null);

  const chat = useMutation({
    mutationFn: (vars: { messages: ArtifactChatMessage[]; forceFinal?: boolean }) =>
      postArtifactChat(researchId, entity, clusterId, selectedFields, vars.messages, vars.forceFinal ?? false, currentDraft !== null),
    onSuccess: (turn, vars) => {
      setMessages([...vars.messages, { role: "assistant", content: turn.message }]);
      if (turn.type === "final") {
        setCurrentDraft(turn.artifact);
        void queryClient.invalidateQueries({ queryKey: ["research", researchId] });
      }
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
    setCurrentDraft(null);
    setStage("chatting");
    chat.mutate({ messages: [] });
  }

  function sendReply() {
    const content = replyDraft.trim();
    if (!content) return;
    setReplyDraft("");
    setStage("chatting");
    chat.mutate({ messages: [...messages, { role: "user", content }] });
  }

  function generateNow() {
    const content = replyDraft.trim();
    const nextMessages = content ? [...messages, { role: "user" as const, content }] : messages;
    setReplyDraft("");
    setStage("chatting");
    chat.mutate({ messages: nextMessages, forceFinal: true });
  }

  function closeDialog() {
    setStage("idle");
    setMessages([]);
    setReplyDraft("");
    setCurrentDraft(null);
  }

  return <div className="space-y-2">
    {artifact && stage === "idle" ? <DraftSummary draft={artifact} onUse={() => restore.mutate()} useIsPending={restore.isPending} /> : null}
    {artifact && stage === "idle" ? <div className="flex gap-2">
      <Button type="button" onClick={() => setStage("selecting")}>{t("Generate again")}</Button>
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
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={closeDialog}>{t("Cancel")}</Button>
          <Button type="button" variant="primary" disabled={chat.isPending} onClick={startChat}>{t("Continue")}</Button>
        </div>
      </div>
    </Dialog>

    <Dialog open={stage === "chatting"} onClose={closeDialog} title={t("Generate artifacts")} className="max-w-3xl">
      <div className="space-y-4">
        <div className="max-h-96 space-y-2 overflow-y-auto rounded-md border border-border bg-muted/20 p-3">
          {messages.map((message, index) => <div key={index} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <p className={message.role === "user"
              ? "max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground"
              : "max-w-[80%] rounded-lg bg-card px-3 py-2 text-sm text-card-foreground"}>
              {message.content}
            </p>
          </div>)}
        </div>

        {currentDraft ? <DraftSummary draft={currentDraft} onUse={() => restore.mutate()} useIsPending={restore.isPending} /> : null}
        {restore.error ? <p role="alert" className="text-sm text-destructive">{restore.error.message}</p> : null}

        <Textarea aria-label={t("Your reply")} value={replyDraft} onChange={(event) => setReplyDraft(event.target.value)} rows={3} />
        {chat.error ? <p role="alert" className="text-sm text-destructive">{chat.error.message}</p> : null}
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" onClick={closeDialog}>{t("Cancel")}</Button>
          {replyDraft.trim() || messages.some((message) => message.role === "user") ? (
            <Button type="button" disabled={chat.isPending} onClick={generateNow}>{t("Generate Now")}</Button>
          ) : null}
          <Button type="button" variant="primary" disabled={chat.isPending || !replyDraft.trim()} onClick={sendReply}>{t("Send")}</Button>
        </div>
      </div>
    </Dialog>
  </div>;
}
