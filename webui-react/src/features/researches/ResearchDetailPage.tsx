import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { getResearch, type ReportCluster, type ResearchArtifact } from "@/api/research";
import { ArtifactChat } from "./ArtifactChat";

const TERMINAL_STATUSES = new Set(["completed", "failed"]);

interface RankedCandidate {
  candidate_id: string;
  cluster_id?: string;
  title?: string;
  url?: string;
  explanation?: string;
  snippet?: string;
}

interface RawReport {
  clusters?: ReportCluster[];
  ranked_candidates?: RankedCandidate[];
}

function ClusterCard({ researchId, entity, cluster, candidates, rank, artifact }: {
  researchId: string;
  entity: string;
  cluster: ReportCluster;
  candidates: RankedCandidate[];
  rank: number;
  artifact?: ResearchArtifact;
}) {
  const { t } = useTranslation();
  const candidateIds = new Set(Array.isArray(cluster.candidate_ids) ? cluster.candidate_ids as string[] : []);
  const evidence = candidates.filter((candidate) => candidate.cluster_id === cluster.cluster_id || candidateIds.has(candidate.candidate_id));
  const explanations = [...new Set(evidence.map((candidate) => candidate.explanation).filter(Boolean))] as string[];

  return <article className="space-y-3 rounded-lg border border-border bg-card p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">#{rank}</p>
        <h3 className="font-semibold">{cluster.title || cluster.cluster_id}</h3>
      </div>
      {cluster.score !== undefined ? <span className="rounded-full bg-muted px-2 py-1 text-xs">{t("Score")}: {cluster.score}</span> : null}
    </div>
    {cluster.sources?.length ? <p className="text-xs text-muted-foreground">{t("Sources")}: {cluster.sources.join(", ")}</p> : null}
    {explanations.length ? <div>
      <h4 className="text-sm font-medium">{t("Why ranked")}</h4>
      {explanations.map((explanation) => <p key={explanation} className="text-sm text-muted-foreground">{explanation}</p>)}
    </div> : null}
    {evidence.some((candidate) => candidate.url) ? <div>
      <h4 className="text-sm font-medium">{t("Links")}</h4>
      <ul className="list-inside list-disc text-sm">
        {evidence.filter((candidate) => candidate.url).map((candidate) => <li key={candidate.candidate_id}>
          <a className="text-primary underline" href={candidate.url} target="_blank" rel="noreferrer">{candidate.title || candidate.url}</a>
        </li>)}
      </ul>
    </div> : null}
    <ArtifactChat researchId={researchId} entity={entity} clusterId={cluster.cluster_id} artifact={artifact} />
  </article>;
}

export function ResearchDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const research = useQuery({
    queryKey: ["research", id],
    queryFn: () => getResearch(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => TERMINAL_STATUSES.has(query.state.data?.status ?? "") ? false : 1_500,
  });

  if (research.isPending) return <div className="p-4">{t("Loading...")}</div>;
  if (research.error) return <div className="p-4"><p role="alert" className="text-sm text-destructive">{research.error.message}</p></div>;

  const data = research.data;
  return <div className="space-y-6 p-4">
    <div className="space-y-2">
      <Link className="text-sm text-primary underline" to="/researches">← {t("Researches")}</Link>
      <h1 className="text-xl font-semibold">{data.topic}</h1>
      <p className="text-sm text-muted-foreground">{t("Status")}: <span role="status">{data.status}</span> · {data.depth} · {data.sources.join(", ")}</p>
    </div>

    {data.status === "failed" ? <p role="alert" className="rounded border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">{data.error_message || t("Research failed.")}</p> : null}
    {data.status === "pending" || data.status === "running" ? <p className="text-sm text-muted-foreground">{t("Research is running. This page updates automatically.")}</p> : null}

    {data.status === "completed" && data.report_json ? data.report_json.entities.map((entityReport, entityIndex) => {
      const report = entityReport.report as RawReport;
      const candidates = report.ranked_candidates ?? [];
      return <section key={`${entityReport.entity}-${entityIndex}`} className="space-y-3">
        {data.report_json && data.report_json.entities.length > 1 ? <h2 className="text-lg font-semibold">{entityReport.entity}</h2> : null}
        {(report.clusters ?? []).map((cluster, index) => <ClusterCard
          key={cluster.cluster_id}
          researchId={data.id}
          entity={entityReport.entity}
          cluster={cluster}
          candidates={candidates}
          rank={index + 1}
          artifact={data.artifacts?.find((item) => item.entity === entityReport.entity && item.cluster_id === cluster.cluster_id)}
        />)}
        {(report.clusters?.length ?? 0) === 0 ? <p className="text-sm text-muted-foreground">{t("No clusters found.")}</p> : null}
      </section>;
    }) : null}
  </div>;
}
