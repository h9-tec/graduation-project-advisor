"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { fetchCards, type LeanCard, type RefineResponse } from "@/lib/api";
import { IdeaCard } from "@/components/idea-card";
import { RefineBar } from "@/components/refine-bar";

export function BoardView({
  locale,
  sessionId,
}: {
  locale: string;
  sessionId: string;
}) {
  const t = useTranslations("board");
  const [cards, setCards] = useState<LeanCard[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [refinementCount, setRefinementCount] = useState(0);
  const [historyDepth, setHistoryDepth] = useState(0);

  useEffect(() => {
    // remember which session is "active" so /saved can find it
    try {
      localStorage.setItem("grad:last_session", sessionId);
    } catch {
      // ignore
    }
    let cancelled = false;
    fetchCards(sessionId)
      .then((c) => {
        if (!cancelled) setCards(c);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  function onRefined(r: RefineResponse) {
    setCards(r.cards);
    setRefinementCount(r.refinement_count);
    setHistoryDepth(r.history_depth);
    setErr(null);
  }

  return (
    <section className="flex flex-col gap-10">
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p
            className="font-mono text-xs uppercase tracking-[0.3em]"
            style={{ color: "var(--color-accent-strong)" }}
          >
            {t("eyebrow")}
          </p>
          <h1
            className="mt-3 text-4xl leading-tight md:text-6xl"
            style={{ fontWeight: 800 }}
          >
            {t("headline")}
          </h1>
          <p
            className="mt-3 max-w-2xl text-base md:text-lg"
            style={{ color: "var(--color-text-muted)" }}
          >
            {t("subhead")}
          </p>
        </div>
        <Link
          href={`/${locale}/onboard`}
          className="inline-flex items-center gap-2 rounded-full border px-5 py-2 text-sm transition-all hover:translate-y-[-1px]"
          style={{
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {t("tryAgain")}
        </Link>
      </header>

      {err ? (
        <div
          className="rounded-md border px-4 py-6 text-sm"
          role="alert"
          style={{
            borderColor: "var(--color-signal-warn)",
            color: "var(--color-signal-warn)",
            background:
              "color-mix(in srgb, var(--color-signal-warn) 10%, transparent)",
          }}
        >
          {err}
        </div>
      ) : cards === null ? (
        <div
          className="flex min-h-[40vh] items-center justify-center rounded-lg border border-dashed text-sm"
          style={{
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-muted)",
          }}
        >
          {t("loading")}
        </div>
      ) : cards.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)" }}>{t("empty")}</p>
      ) : (
        <div className="grid auto-rows-[minmax(0,1fr)] grid-cols-1 gap-5 md:grid-cols-3 md:gap-6">
          {cards.map((c, i) => (
            <IdeaCard
              key={`${c.id}-${refinementCount}`}
              locale={locale}
              sessionId={sessionId}
              card={c}
              index={i}
            />
          ))}
        </div>
      )}

      {cards !== null ? (
        <RefineBar
          sessionId={sessionId}
          refinementCount={refinementCount}
          historyDepth={historyDepth}
          onRefined={onRefined}
        />
      ) : null}
    </section>
  );
}
