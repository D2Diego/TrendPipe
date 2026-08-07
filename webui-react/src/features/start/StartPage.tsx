import { ArrowRight, Lightbulb, Search, Video } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const cardClass = "group flex min-h-72 flex-col rounded-2xl border border-border bg-card p-7 shadow-lg transition duration-200 hover:-translate-y-1 hover:border-primary/70 hover:shadow-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function StartPage() {
  const { t } = useTranslation();

  return <section className="mx-auto flex min-h-[calc(100vh-74px)] max-w-6xl flex-col justify-center px-4 py-12 sm:px-8">
    <div className="mx-auto mb-10 max-w-3xl text-center">
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
        <Lightbulb className="size-4" />{t("From idea to video")}
      </div>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t("How do you want to start?")}</h1>
      <p className="mt-4 text-base text-muted-foreground sm:text-lg">{t("Choose the workflow that best matches where your idea is now.")}</p>
    </div>

    <div className="grid gap-5 md:grid-cols-2">
      <Link className={cardClass} to="/researches" aria-label={t("Develop an idea with research")}>
        <div className="mb-6 flex size-12 items-center justify-center rounded-xl bg-primary/15 text-primary"><Search className="size-6" /></div>
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">{t("Research assistance")}</p>
        <h2 className="text-2xl font-semibold">{t("Develop an idea with research")}</h2>
        <p className="mt-3 flex-1 leading-relaxed text-muted-foreground">{t("Use the researcher to discover angles, evidence, trends, and sources before creating your video.")}</p>
        <span className="mt-7 inline-flex items-center gap-2 font-semibold text-primary">{t("Start with research")}<ArrowRight className="size-4 transition-transform group-hover:translate-x-1" /></span>
      </Link>

      <Link className={cardClass} to="/generate" aria-label={t("I already have an idea")}>
        <div className="mb-6 flex size-12 items-center justify-center rounded-xl bg-primary/15 text-primary"><Video className="size-6" /></div>
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">{t("Direct creation")}</p>
        <h2 className="text-2xl font-semibold">{t("I already have an idea")}</h2>
        <p className="mt-3 flex-1 leading-relaxed text-muted-foreground">{t("Go straight to the video generator to write or paste your script and configure the production.")}</p>
        <span className="mt-7 inline-flex items-center gap-2 font-semibold text-primary">{t("Open video generator")}<ArrowRight className="size-4 transition-transform group-hover:translate-x-1" /></span>
      </Link>
    </div>
  </section>;
}
