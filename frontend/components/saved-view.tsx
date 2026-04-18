"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { listSaved, unsaveCard, type LeanCard } from "@/lib/api";

type Props = {
  locale: string;
};

const MAX_COMPARE = 3;

export function SavedView({ locale }: Props) {
  const t = useTranslations("saved");
  const tc = useTranslations("board");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [cards, setCards] = useState<LeanCard[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    try {
      setSessionId(localStorage.getItem("grad:last_session"));
    } catch {
      setSessionId(null);
    }
  }, []);

  useEffect(() => {
    if (!sessionId) {
      setCards([]);
      return;
    }
    let cancelled = false;
    listSaved(sessionId)
      .then((r) => {
        if (!cancelled) setCards(r.cards);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const toggleSelect = useCallback(
    (cardId: string) => {
      setSelected((prev) => {
        if (prev.includes(cardId)) {
          return prev.filter((c) => c !== cardId);
        }
        if (prev.length >= MAX_COMPARE) {
          return [...prev.slice(1), cardId];
        }
        return [...prev, cardId];
      });
    },
    [],
  );

  const onUnsave = useCallback(
    async (cardId: string) => {
      if (!sessionId) return;
      try {
        const r = await unsaveCard(sessionId, cardId);
        setCards(r.cards);
        setSelected((prev) => prev.filter((c) => c !== cardId));
      } catch {
        // ignore — next list reload will catch
      }
    },
    [sessionId],
  );

  const selectedCards = useMemo(
    () => (cards ?? []).filter((c) => selected.includes(c.id)),
    [cards, selected],
  );

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
        <div className="flex flex-wrap gap-2">
          <Link
            href={
              sessionId ? `/${locale}/board/${sessionId}` : `/${locale}/onboard`
            }
            className="inline-flex items-center gap-2 rounded-full border px-5 py-2 text-sm transition-all hover:translate-y-[-1px]"
            style={{
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            {t("backToBoard")}
          </Link>
          <button
            type="button"
            onClick={() => {
              setCompareMode((v) => !v);
              setSelected([]);
            }}
            disabled={(cards ?? []).length === 0}
            className="inline-flex items-center gap-2 rounded-full px-5 py-2 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 hover:translate-y-[-1px]"
            style={{
              background: compareMode
                ? "var(--color-surface)"
                : "var(--color-accent)",
              color: compareMode
                ? "var(--color-text-primary)"
                : "var(--color-elevated)",
              borderColor: "var(--color-border-subtle)",
              borderWidth: compareMode ? 1 : 0,
              borderStyle: "solid",
            }}
          >
            {compareMode ? t("stopCompare") : t("compare")}
          </button>
        </div>
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
        <p style={{ color: "var(--color-text-muted)" }}>{tc("loading")}</p>
      ) : cards.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)" }}>{t("empty")}</p>
      ) : compareMode && selectedCards.length > 0 ? (
        <ComparePanel cards={selectedCards} />
      ) : null}

      {cards !== null && cards.length > 0 ? (
        <div className="flex flex-col gap-4">
          {compareMode ? (
            <p
              className="font-mono text-xs uppercase tracking-widest"
              style={{ color: "var(--color-text-muted)" }}
            >
              {t("compareHint")} · {t("compareSelected", { count: selected.length })}
            </p>
          ) : null}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3 md:gap-6">
            {cards.map((c) => (
              <SavedCard
                key={c.id}
                card={c}
                compareMode={compareMode}
                checked={selected.includes(c.id)}
                onToggle={() => toggleSelect(c.id)}
                onUnsave={() => onUnsave(c.id)}
                blueprintHref={
                  sessionId
                    ? `/${locale}/blueprint/${sessionId}/${c.id}`
                    : undefined
                }
                locale={locale}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SavedCard({
  card,
  compareMode,
  checked,
  onToggle,
  onUnsave,
  blueprintHref,
  locale,
}: {
  card: LeanCard;
  compareMode: boolean;
  checked: boolean;
  onToggle: () => void;
  onUnsave: () => void;
  blueprintHref: string | undefined;
  locale: string;
}) {
  return (
    <article
      className="surface-card relative flex flex-col gap-3 rounded-2xl p-5"
      style={{
        outline: checked
          ? "2px solid var(--color-accent)"
          : "2px solid transparent",
        outlineOffset: -2,
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className="font-mono text-[11px] uppercase tracking-widest"
          style={{ color: "var(--color-accent-strong)" }}
        >
          ♥ {card.stars_estimate.toLocaleString("en-US")}
        </span>
        <div className="flex gap-1">
          {compareMode ? (
            <button
              type="button"
              onClick={onToggle}
              aria-pressed={checked}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
              style={{
                background: checked
                  ? "var(--color-accent)"
                  : "var(--color-surface)",
                color: checked
                  ? "var(--color-elevated)"
                  : "var(--color-text-muted)",
              }}
            >
              {checked ? "✓" : ""}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onUnsave}
            aria-label="Unsave"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-base"
            style={{
              background:
                "color-mix(in srgb, var(--color-accent) 20%, transparent)",
              color: "var(--color-accent-strong)",
            }}
          >
            ♥
          </button>
        </div>
      </div>

      <h3 className="text-xl leading-tight" style={{ fontWeight: 700 }}>
        {card.title}
      </h3>

      <p
        className="text-sm leading-relaxed"
        style={{ color: "var(--color-text-primary)" }}
      >
        {card.why_fit}
      </p>

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-2 font-mono text-[11px] uppercase tracking-widest">
        <span
          className="rounded-full px-2 py-1"
          style={{
            background:
              "color-mix(in srgb, var(--color-signal-code) 10%, transparent)",
            color: "var(--color-signal-code)",
          }}
        >
          {card.est_weeks} wks
        </span>
        <span
          className="rounded-full px-2 py-1"
          style={{
            background:
              "color-mix(in srgb, var(--color-accent) 10%, transparent)",
            color: "var(--color-accent-strong)",
          }}
        >
          {card.difficulty_verdict}
        </span>
        {blueprintHref ? (
          <a
            href={blueprintHref}
            className="ms-auto underline"
            style={{ color: "var(--color-accent-strong)" }}
          >
            {locale === "ar" ? "→ الخطة" : "Blueprint →"}
          </a>
        ) : null}
      </div>
    </article>
  );
}

function ComparePanel({ cards }: { cards: LeanCard[] }) {
  return (
    <section
      className="surface-card rounded-2xl p-5"
      aria-label="Compare"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {cards.map((c) => (
          <div
            key={c.id}
            className="flex flex-col gap-3 rounded-xl border p-4 text-sm leading-relaxed"
            style={{
              borderColor: "var(--color-border-subtle)",
              background: "var(--color-elevated)",
            }}
          >
            <h4
              className="text-lg leading-tight"
              style={{ fontWeight: 700 }}
            >
              {c.title}
            </h4>
            <p style={{ color: "var(--color-text-primary)" }}>{c.why_fit}</p>
            <dl
              className="flex flex-col gap-1 font-mono text-[11px] uppercase tracking-widest"
              style={{ color: "var(--color-text-muted)" }}
            >
              <div className="flex justify-between">
                <dt>Weeks</dt>
                <dd>{c.est_weeks}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Difficulty</dt>
                <dd>{c.difficulty_verdict}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Stars</dt>
                <dd>{c.stars_estimate.toLocaleString("en-US")}</dd>
              </div>
            </dl>
            {c.github_url ? (
              <a
                href={c.github_url}
                target="_blank"
                rel="noreferrer"
                className="font-mono text-xs break-all"
                style={{ color: "var(--color-accent-strong)" }}
              >
                {c.github_url}
              </a>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
