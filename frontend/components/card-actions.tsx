"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import {
  postFeedback,
  saveCard,
  unsaveCard,
  type Reaction,
} from "@/lib/api";

type Props = {
  sessionId: string;
  cardId: string;
};

type Persisted = {
  reaction?: Reaction;
  saved?: boolean;
};

function _storageKey(sessionId: string, cardId: string): string {
  return `grad:card:${sessionId}:${cardId}`;
}

function readPersisted(sessionId: string, cardId: string): Persisted {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(_storageKey(sessionId, cardId));
    return raw ? (JSON.parse(raw) as Persisted) : {};
  } catch {
    return {};
  }
}

function writePersisted(
  sessionId: string,
  cardId: string,
  patch: Persisted,
): void {
  if (typeof window === "undefined") return;
  try {
    const key = _storageKey(sessionId, cardId);
    const next = { ...readPersisted(sessionId, cardId), ...patch };
    localStorage.setItem(key, JSON.stringify(next));
  } catch {
    // ignore quota / private-mode errors; state will just not persist
  }
}

export function CardActions({ sessionId, cardId }: Props) {
  const t = useTranslations("cardActions");
  const [reaction, setReaction] = useState<Reaction | undefined>(undefined);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  // hydrate from localStorage on mount — keeps per-card state sticky
  // across refreshes within the same session
  useEffect(() => {
    const persisted = readPersisted(sessionId, cardId);
    setReaction(persisted.reaction);
    setSaved(Boolean(persisted.saved));
  }, [sessionId, cardId]);

  const onReact = useCallback(
    async (next: Reaction) => {
      if (busy) return;
      setBusy(true);
      const optimistic = reaction === next ? undefined : next;
      setReaction(optimistic);
      writePersisted(sessionId, cardId, { reaction: optimistic });
      try {
        // only POST when toggling ON; toggling OFF is client-only
        // (feedback is append-only on the server)
        if (optimistic !== undefined) {
          await postFeedback(sessionId, cardId, optimistic);
        }
      } catch {
        setReaction(reaction);
        writePersisted(sessionId, cardId, { reaction });
      } finally {
        setBusy(false);
      }
    },
    [busy, reaction, sessionId, cardId],
  );

  const onToggleSave = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    const next = !saved;
    setSaved(next);
    writePersisted(sessionId, cardId, { saved: next });
    try {
      if (next) {
        await saveCard(sessionId, cardId);
      } else {
        await unsaveCard(sessionId, cardId);
      }
    } catch {
      setSaved(!next);
      writePersisted(sessionId, cardId, { saved: !next });
    } finally {
      setBusy(false);
    }
  }, [busy, saved, sessionId, cardId]);

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        onClick={() => onReact("up")}
        aria-pressed={reaction === "up"}
        aria-label={t("thumbsUp")}
        title={t("thumbsUp")}
        disabled={busy}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm transition-all hover:translate-y-[-1px] disabled:opacity-60"
        style={{
          background:
            reaction === "up"
              ? "color-mix(in srgb, var(--color-signal-code) 16%, transparent)"
              : "transparent",
          color:
            reaction === "up"
              ? "var(--color-signal-code)"
              : "var(--color-text-muted)",
        }}
      >
        ▲
      </button>
      <button
        type="button"
        onClick={() => onReact("down")}
        aria-pressed={reaction === "down"}
        aria-label={t("thumbsDown")}
        title={t("thumbsDown")}
        disabled={busy}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm transition-all hover:translate-y-[-1px] disabled:opacity-60"
        style={{
          background:
            reaction === "down"
              ? "color-mix(in srgb, var(--color-signal-paper) 16%, transparent)"
              : "transparent",
          color:
            reaction === "down"
              ? "var(--color-signal-paper)"
              : "var(--color-text-muted)",
        }}
      >
        ▼
      </button>
      <button
        type="button"
        onClick={onToggleSave}
        aria-pressed={saved}
        aria-label={saved ? t("unsave") : t("save")}
        title={saved ? t("unsave") : t("save")}
        disabled={busy}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm transition-all hover:translate-y-[-1px] disabled:opacity-60"
        style={{
          background: saved
            ? "color-mix(in srgb, var(--color-accent) 20%, transparent)"
            : "transparent",
          color: saved ? "var(--color-accent-strong)" : "var(--color-text-muted)",
        }}
      >
        {saved ? "♥" : "♡"}
      </button>
    </div>
  );
}
