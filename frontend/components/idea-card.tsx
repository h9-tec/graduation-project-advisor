import Link from "next/link";
import { useTranslations } from "next-intl";

import type { LeanCard } from "@/lib/api";
import { CardActions } from "@/components/card-actions";

export function IdeaCard({
  locale,
  sessionId,
  card,
  index,
}: {
  locale: string;
  sessionId: string;
  card: LeanCard;
  index: number;
}) {
  const t = useTranslations("board");

  // Varied card heights so the grid doesn't feel uniform.
  const heightClass =
    index % 4 === 0
      ? "md:col-span-2 md:row-span-2"
      : index % 3 === 0
        ? "md:col-span-2"
        : "";

  return (
    <article
      className={`surface-card fade-rise relative flex h-full flex-col gap-4 rounded-2xl p-6 ${heightClass}`}
      style={{ animationDelay: `${80 + index * 80}ms` }}
    >
      {/* Rank tag */}
      <div className="flex items-center justify-between gap-4">
        <span
          className="font-mono text-xs uppercase tracking-widest"
          style={{ color: "var(--color-accent-strong)" }}
        >
          {t("rankLabel")}
          {card.rank}
        </span>
        <span
          className="font-mono text-xs"
          style={{ color: "var(--color-text-muted)" }}
        >
          {t("cardStars")} {card.stars_estimate.toLocaleString("en-US")}
        </span>
      </div>

      {/* Domains chips */}
      <div className="flex flex-wrap gap-1.5">
        {card.domains.slice(0, 3).map((d) => (
          <span
            key={d}
            className="rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest"
            style={{
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-muted)",
            }}
          >
            {d}
          </span>
        ))}
      </div>

      <h3
        className="text-2xl leading-tight md:text-3xl"
        style={{ fontWeight: 700 }}
      >
        {card.title}
      </h3>

      <p
        className="text-sm leading-relaxed"
        style={{ color: "var(--color-text-primary)" }}
      >
        {card.why_fit}
      </p>

      {card.research_hook ? (
        <p
          className="text-xs italic leading-relaxed"
          style={{ color: "var(--color-text-muted)" }}
        >
          {card.research_hook}
        </p>
      ) : null}

      {/* Hairline divider */}
      <div
        aria-hidden
        className="my-2 h-px w-full"
        style={{ background: "var(--color-accent)", opacity: 0.35 }}
      />

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-widest">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-1"
          style={{
            background: "color-mix(in srgb, var(--color-signal-code) 10%, transparent)",
            color: "var(--color-signal-code)",
          }}
        >
          ✓ {card.est_weeks} {t("cardWeeks")}
        </span>
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-1"
          style={{
            background: "color-mix(in srgb, var(--color-accent) 10%, transparent)",
            color: "var(--color-accent-strong)",
          }}
        >
          △ {card.difficulty_verdict}
        </span>
      </div>

      <div className="mt-auto flex items-center justify-between gap-2">
        <Link
          href={`/${locale}/blueprint/${sessionId}/${card.id}`}
          className="group inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all hover:translate-y-[-1px]"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-elevated)",
          }}
        >
          {t("cardExpand")}
          <span aria-hidden className="transition-transform group-hover:translate-x-0.5">
            {locale === "ar" ? "←" : "→"}
          </span>
        </Link>
        <CardActions sessionId={sessionId} cardId={card.id} />
      </div>
    </article>
  );
}
