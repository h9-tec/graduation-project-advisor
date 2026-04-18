"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  MAX_REFINEMENTS_PER_SESSION,
  refineSession,
  undoRefinement,
  type LeanCard,
  type RefineResponse,
} from "@/lib/api";

type Props = {
  sessionId: string;
  refinementCount: number;
  historyDepth: number;
  onRefined: (r: RefineResponse) => void;
};

export function RefineBar({
  sessionId,
  refinementCount,
  historyDepth,
  onRefined,
}: Props) {
  const t = useTranslations("refine");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [lastNote, setLastNote] = useState<string | null>(null);

  const atLimit = refinementCount >= MAX_REFINEMENTS_PER_SESSION;
  const canSubmit = !busy && !atLimit && message.trim().length > 0;
  const canUndo = !busy && historyDepth > 0;

  async function submit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await refineSession(sessionId, message.trim());
      setLastNote(r.assistant_msg);
      setMessage("");
      onRefined(r);
    } catch (caught) {
      setErr(caught instanceof Error ? caught.message : t("error"));
    } finally {
      setBusy(false);
    }
  }

  async function undo() {
    if (!canUndo) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await undoRefinement(sessionId);
      setLastNote(r.assistant_msg);
      onRefined(r);
    } catch (caught) {
      setErr(caught instanceof Error ? caught.message : t("error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="sticky bottom-4 z-20 mx-auto mt-8 w-full"
      aria-label={t("heading")}
    >
      <div
        className="surface-card flex flex-col gap-3 rounded-2xl p-4 shadow-xl"
        style={{ backdropFilter: "blur(8px)" }}
      >
        {lastNote ? (
          <p
            className="text-sm"
            style={{ color: "var(--color-text-muted)" }}
            role="status"
          >
            <span
              aria-hidden
              className="me-2 font-mono text-xs"
              style={{ color: "var(--color-accent-strong)" }}
            >
              ✎
            </span>
            {lastNote}
          </p>
        ) : null}

        <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t("placeholder")}
            maxLength={500}
            disabled={busy || atLimit}
            className="min-w-0 flex-1 rounded-full border px-5 py-3 text-sm"
            style={{
              background: "var(--color-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
            aria-label={t("placeholder")}
          />
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 hover:translate-y-[-1px]"
            style={{
              background: "var(--color-accent)",
              color: "var(--color-elevated)",
            }}
          >
            {busy ? t("busy") : t("submit")}
          </button>
          <button
            type="button"
            onClick={undo}
            disabled={!canUndo}
            className="inline-flex items-center gap-2 rounded-full border px-4 py-3 text-sm transition-all disabled:cursor-not-allowed disabled:opacity-40 hover:translate-y-[-1px]"
            style={{
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
            aria-label={t("undo")}
          >
            ↶ {t("undo")}
          </button>
        </form>

        <div
          className="flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] uppercase tracking-widest"
          style={{ color: "var(--color-text-muted)" }}
        >
          <span>
            {t("counter", {
              count: refinementCount,
              max: MAX_REFINEMENTS_PER_SESSION,
            })}
          </span>
          {atLimit ? (
            <span style={{ color: "var(--color-signal-warn)" }}>
              {t("limitReached")}
            </span>
          ) : null}
          {err ? (
            <span
              style={{ color: "var(--color-signal-warn)" }}
              role="alert"
            >
              {err}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
