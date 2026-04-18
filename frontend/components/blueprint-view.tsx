"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { expandCard, type Blueprint } from "@/lib/api";

export function BlueprintView({
  locale,
  sessionId,
  cardId,
}: {
  locale: string;
  sessionId: string;
  cardId: string;
}) {
  const t = useTranslations("blueprint");
  const [bp, setBp] = useState<Blueprint | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    expandCard(sessionId, cardId)
      .then((res) => {
        if (!cancelled) setBp(res.blueprint);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, cardId]);

  if (err) {
    return (
      <div className="flex flex-col gap-6">
        <Link
          href={`/${locale}/board/${sessionId}`}
          className="text-sm"
          style={{ color: "var(--color-accent-strong)" }}
        >
          {t("back")}
        </Link>
        <p
          className="rounded-md border px-4 py-6 text-sm"
          role="alert"
          style={{
            borderColor: "var(--color-signal-warn)",
            color: "var(--color-signal-warn)",
            background:
              "color-mix(in srgb, var(--color-signal-warn) 10%, transparent)",
          }}
        >
          {t("error")} — {err}
        </p>
      </div>
    );
  }

  if (!bp) {
    return (
      <div
        className="flex min-h-[60vh] items-center justify-center rounded-lg border border-dashed text-sm"
        style={{
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-muted)",
        }}
      >
        {t("loading")}
      </div>
    );
  }

  return (
    <article className="fade-rise flex flex-col gap-10">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href={`/${locale}/board/${sessionId}`}
          className="font-mono text-xs uppercase tracking-[0.3em]"
          style={{ color: "var(--color-accent-strong)" }}
        >
          {t("back")}
        </Link>
        <span
          className="font-mono text-xs uppercase tracking-[0.3em]"
          style={{ color: "var(--color-text-muted)" }}
        >
          {t("eyebrow")}
        </span>
      </header>

      <section className="flex flex-col gap-3">
        <h1
          className="text-3xl leading-tight md:text-5xl"
          style={{ fontWeight: 800 }}
        >
          {t("problem")}
        </h1>
        <p className="text-lg leading-relaxed">{bp.problem_statement}</p>
      </section>

      <Section title={t("whyMatters")}>
        <p className="leading-relaxed">{bp.why_it_matters}</p>
      </Section>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <Section title={t("inScope")}>
          <BulletList items={bp.in_scope} marker="✓" markerColor="signal-code" />
        </Section>
        <Section title={t("outOfScope")}>
          <BulletList
            items={bp.out_of_scope}
            marker="⊘"
            markerColor="signal-paper"
          />
        </Section>
      </div>

      <Section title={t("arch")}>
        <div
          className="rounded-lg border p-5 text-sm leading-relaxed"
          style={{
            borderColor: "var(--color-border-subtle)",
            background: "color-mix(in srgb, var(--color-surface) 70%, transparent)",
            whiteSpace: "pre-wrap",
          }}
        >
          {bp.suggested_architecture}
        </div>
      </Section>

      <Section title={t("stack")}>
        <div className="flex flex-wrap gap-2">
          {bp.tech_stack.map((s) => (
            <span
              key={s}
              className="rounded-md border px-3 py-1.5 font-mono text-xs"
              style={{
                borderColor: "var(--color-border-subtle)",
                background: "var(--color-surface)",
              }}
            >
              {s}
            </span>
          ))}
        </div>
      </Section>

      <Section title={t("milestones")}>
        <ol className="flex flex-col gap-3">
          {bp.milestones_by_week.map((m, i) => (
            <li
              key={`${m.weeks}-${i}`}
              className="flex gap-4 rounded-lg border p-4"
              style={{ borderColor: "var(--color-border-subtle)" }}
            >
              <span
                className="shrink-0 font-mono text-sm font-semibold"
                style={{ color: "var(--color-accent-strong)" }}
              >
                {m.weeks}
              </span>
              <ul className="flex list-disc flex-col gap-1.5 ps-4 text-sm leading-relaxed">
                {m.goals.map((g, j) => (
                  <li key={j}>{g}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </Section>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <Section title={t("datasets")}>
          <ul className="flex flex-col gap-3">
            {bp.datasets.map((d, i) => (
              <li
                key={i}
                className="rounded-lg border p-3 text-sm"
                style={{ borderColor: "var(--color-border-subtle)" }}
              >
                <div className="font-semibold">{d.name}</div>
                {d.url ? (
                  <a
                    href={d.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-xs break-all"
                    style={{ color: "var(--color-accent-strong)" }}
                  >
                    {d.url}
                  </a>
                ) : null}
                {d.note ? (
                  <p
                    className="mt-1"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    {d.note}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </Section>
        <Section title={t("metrics")}>
          <BulletList items={bp.evaluation_metrics} marker="•" markerColor="accent" />
        </Section>
      </div>

      <Section title={t("risks")}>
        <ul className="flex flex-col gap-3">
          {bp.risks_and_mitigations.map((r, i) => (
            <li
              key={i}
              className="flex flex-col gap-1 rounded-lg border p-4"
              style={{ borderColor: "var(--color-border-subtle)" }}
            >
              <span className="font-semibold">
                <span
                  className="me-2 font-mono text-xs"
                  style={{ color: "var(--color-signal-warn)" }}
                >
                  ⚠
                </span>
                {r.risk}
              </span>
              <span
                className="text-sm"
                style={{ color: "var(--color-text-muted)" }}
              >
                → {r.mitigation}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={t("standOut")}>
        <BulletList items={bp.how_to_stand_out} marker="★" markerColor="accent" />
      </Section>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <Section title={t("papers")}>
          <ul className="flex flex-col gap-2 text-sm">
            {bp.paper_refs.map((p, i) => (
              <li key={i}>
                <span className="font-semibold">{p.title ?? p.name}</span>
                {p.note ? (
                  <span style={{ color: "var(--color-text-muted)" }}> — {p.note}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </Section>
        <Section title={t("repos")}>
          <ul className="flex flex-col gap-2 text-sm">
            {bp.repo_refs.map((r, i) => (
              <li key={i}>
                <span className="font-mono font-semibold">{r.name ?? r.title}</span>
                {r.note ? (
                  <span style={{ color: "var(--color-text-muted)" }}> — {r.note}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </Section>
      </div>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2
        className="font-mono text-xs uppercase tracking-[0.3em]"
        style={{ color: "var(--color-accent-strong)" }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function BulletList({
  items,
  marker,
  markerColor,
}: {
  items: string[];
  marker: string;
  markerColor: "signal-code" | "signal-paper" | "accent";
}) {
  const colorMap = {
    "signal-code": "var(--color-signal-code)",
    "signal-paper": "var(--color-signal-paper)",
    accent: "var(--color-accent)",
  } as const;

  return (
    <ul className="flex flex-col gap-2 text-sm leading-relaxed">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3">
          <span
            aria-hidden
            className="font-mono"
            style={{ color: colorMap[markerColor] }}
          >
            {marker}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
