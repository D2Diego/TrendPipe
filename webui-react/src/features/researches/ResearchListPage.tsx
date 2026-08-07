import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { deleteResearch, listResearches } from "@/api/research";
import { NewResearchForm } from "./NewResearchForm";

function formatCreatedAt(value: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function ResearchListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const researches = useQuery({
    queryKey: ["researches"],
    queryFn: listResearches,
    refetchInterval: (query) => query.state.data?.researches.some((item) => item.status === "pending" || item.status === "running") ? 3_000 : false,
  });
  const remove = useMutation({
    mutationFn: (researchId: string) => deleteResearch(researchId),
    onSuccess: async () => {
      setPendingDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["researches"] });
    },
  });

  return <div data-testid="research-list-page" className="space-y-6 p-4">
    <section className="space-y-4 rounded-lg border border-border bg-card p-4">
      <h1 className="text-lg font-semibold">{t("New Research")}</h1>
      <NewResearchForm onCreated={(researchId) => navigate(`/researches/${researchId}`)} />
    </section>

    <section className="space-y-3">
      <h2 className="text-base font-semibold">{t("Past Researches")}</h2>
      {researches.isPending ? <p>{t("Loading...")}</p> : null}
      {researches.error ? <p role="alert" className="text-sm text-destructive">{researches.error.message}</p> : null}
      {!researches.isPending && !researches.error && (researches.data?.researches.length ?? 0) === 0 ? <p className="text-sm text-muted-foreground">{t("No researches yet.")}</p> : null}
      {(researches.data?.researches.length ?? 0) > 0 ? <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead><tr className="bg-muted/40 text-left text-muted-foreground">
            <th className="p-3">{t("Topic")}</th><th className="p-3">{t("Depth")}</th><th className="p-3">{t("Status")}</th><th className="p-3">{t("Created")}</th><th className="p-3" />
          </tr></thead>
          <tbody>{researches.data?.researches.map((item) => <tr key={item.id} className="border-t border-border">
            <td className="p-3"><Link className="font-medium text-primary underline" to={`/researches/${item.id}`}>{item.topic}</Link></td>
            <td className="p-3">{item.depth}</td>
            <td className="p-3"><span className="rounded-full bg-muted px-2 py-1 text-xs">{item.status}</span></td>
            <td className="p-3">{formatCreatedAt(item.created_at)}</td>
            <td className="p-3 text-right"><Button type="button" variant="destructive" disabled={item.status === "running" || remove.isPending} onClick={() => setPendingDeleteId(item.id)}>{t("Delete")}</Button></td>
          </tr>)}</tbody>
        </table>
      </div> : null}
    </section>

    <Dialog open={pendingDeleteId !== null} onClose={() => setPendingDeleteId(null)} title={t("Delete Research")}>
      <div className="space-y-4">
        <p>{t("This cannot be undone.")}</p>
        {remove.error ? <p role="alert" className="text-sm text-destructive">{remove.error.message}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={() => setPendingDeleteId(null)}>{t("Cancel")}</Button>
          <Button type="button" variant="destructive" disabled={remove.isPending} onClick={() => pendingDeleteId && remove.mutate(pendingDeleteId)}>{t("Confirm")}</Button>
        </div>
      </div>
    </Dialog>
  </div>;
}
