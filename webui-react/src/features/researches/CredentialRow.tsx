import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/field";
import { ApiError } from "@/api/client";
import { deleteResearchCredential, updateResearchSettings } from "@/api/research";

export function CredentialRow({ credKey, present }: { credKey: string; present: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isPresent, setIsPresent] = useState(present);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);

  useEffect(() => setIsPresent(present), [present]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["research-settings"] });
  const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

  const save = useMutation({
    mutationFn: () => updateResearchSettings({ [credKey]: value }),
    onSuccess: async () => {
      setIsPresent(true);
      setEditing(false);
      setValue("");
      setMessage({ error: false, text: t("Credential Updated", { key: credKey }) });
      await invalidate();
    },
    onError: (error) => setMessage({ error: true, text: errorText(error) }),
  });

  const remove = useMutation({
    mutationFn: () => deleteResearchCredential(credKey),
    onSuccess: async () => {
      setIsPresent(false);
      setEditing(false);
      setValue("");
      setConfirmOpen(false);
      setMessage({ error: false, text: t("Credential Removed", { key: credKey }) });
      await invalidate();
    },
    onError: (error) => {
      setConfirmOpen(false);
      setMessage({ error: true, text: errorText(error) });
    },
  });

  const showInput = editing || !isPresent;

  return <div className="flex flex-col gap-2 rounded border border-border p-3">
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm font-medium">{credKey}</span>
      <span className="text-sm text-muted-foreground">{isPresent ? t("configured") : t("missing")}</span>
    </div>
    {showInput ? <div className="flex flex-wrap items-center gap-2">
      <Input aria-label={credKey} type="password" autoComplete="off" value={value} onChange={(event) => setValue(event.target.value)} />
      <Button type="button" variant="primary" disabled={!value || save.isPending} onClick={() => save.mutate()}>{save.isPending ? t("Saving...") : t("Save")}</Button>
      {editing ? <Button type="button" variant="ghost" onClick={() => { setEditing(false); setValue(""); }}>{t("Cancel")}</Button> : null}
    </div> : <div className="flex items-center gap-2">
      <Button type="button" onClick={() => setEditing(true)}>{t("Change Credential")}</Button>
      <Button type="button" variant="destructive" aria-label={t("Delete Credential", { key: credKey })} onClick={() => setConfirmOpen(true)}><Trash2 className="size-4" /></Button>
    </div>}
    {message ? <p role={message.error ? "alert" : "status"} className={message.error ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>{message.text}</p> : null}
    <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} title={t("Remove Credential Title")}>
      <p className="text-sm text-muted-foreground">{t("Remove Credential Confirm", { key: credKey })}</p>
      <div className="mt-4 flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={() => setConfirmOpen(false)}>{t("Cancel")}</Button>
        <Button type="button" variant="destructive" disabled={remove.isPending} onClick={() => remove.mutate()}>{remove.isPending ? t("Removing...") : t("Remove")}</Button>
      </div>
    </Dialog>
  </div>;
}
