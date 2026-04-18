"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import {
  submitRecommendations,
  type Domain,
  type IntentProfile,
  type SkillLevel,
} from "@/lib/api";

const ALL_DOMAINS: Domain[] = [
  "nlp",
  "cv",
  "rl",
  "agents",
  "rag",
  "robotics",
  "audio",
  "timeseries",
  "mlops",
  "security",
  "iot",
  "web",
  "mobile",
  "data_engineering",
];

const SKILLS: SkillLevel[] = ["beginner", "intermediate", "advanced"];

export function OnboardForm({ locale }: { locale: "en" | "ar" }) {
  const t = useTranslations("onboard");
  const td = useTranslations("domains");
  const ts = useTranslations("skill");
  const router = useRouter();

  const [domains, setDomains] = useState<Set<Domain>>(new Set());
  const [skill, setSkill] = useState<SkillLevel>("intermediate");
  const [months, setMonths] = useState(6);
  const [team, setTeam] = useState(1);
  const [stacksInput, setStacksInput] = useState("python, pytorch, fastapi");
  const [interests, setInterests] = useState("");
  const [avoidInput, setAvoidInput] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canSubmit = useMemo(
    () => domains.size > 0 && !busy,
    [domains.size, busy],
  );

  function toggleDomain(d: Domain) {
    setDomains((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d);
      else next.add(d);
      return next;
    });
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (domains.size === 0) {
      setErr(t("required"));
      return;
    }
    setErr(null);
    setBusy(true);

    const profile: IntentProfile = {
      language: locale,
      domains: Array.from(domains),
      skill_level: skill,
      months_available: months,
      team_size: team,
      preferred_stacks: stacksInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      interests_text: interests.slice(0, 500),
      requires_code_reference: true,
      avoid: avoidInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };

    try {
      const { session_id } = await submitRecommendations(profile);
      router.push(`/${locale}/board/${session_id}`);
    } catch (caught) {
      setErr(caught instanceof Error ? caught.message : t("error"));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="fade-rise flex flex-col gap-10">
      <header>
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
      </header>

      {/* Domains */}
      <fieldset className="flex flex-col gap-3">
        <legend className="text-lg font-semibold">{t("domains")}</legend>
        <p
          className="text-sm"
          style={{ color: "var(--color-text-muted)" }}
        >
          {t("domainsHint")}
        </p>
        <div className="flex flex-wrap gap-2">
          {ALL_DOMAINS.map((d) => {
            const on = domains.has(d);
            return (
              <button
                key={d}
                type="button"
                onClick={() => toggleDomain(d)}
                aria-pressed={on}
                className="rounded-full border px-4 py-2 text-sm transition-all hover:translate-y-[-1px]"
                style={{
                  background: on
                    ? "var(--color-accent)"
                    : "color-mix(in srgb, var(--color-surface) 60%, transparent)",
                  color: on
                    ? "var(--color-elevated)"
                    : "var(--color-text-primary)",
                  borderColor: on
                    ? "var(--color-accent-strong)"
                    : "var(--color-border-subtle)",
                }}
              >
                {td(d)}
              </button>
            );
          })}
        </div>
      </fieldset>

      {/* Skill + Months + Team in a row */}
      <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
        <fieldset className="flex flex-col gap-3">
          <legend className="text-lg font-semibold">{t("skill")}</legend>
          <div
            className="inline-flex overflow-hidden rounded-full border"
            style={{ borderColor: "var(--color-border-subtle)" }}
          >
            {SKILLS.map((s) => {
              const on = skill === s;
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSkill(s)}
                  className="px-4 py-2 text-sm"
                  style={{
                    background: on ? "var(--color-accent)" : "transparent",
                    color: on
                      ? "var(--color-elevated)"
                      : "var(--color-text-muted)",
                  }}
                  aria-pressed={on}
                >
                  {ts(s)}
                </button>
              );
            })}
          </div>
        </fieldset>

        <label className="flex flex-col gap-3">
          <span className="text-lg font-semibold">{t("months")}</span>
          <input
            type="range"
            min={2}
            max={12}
            value={months}
            onChange={(e) => setMonths(parseInt(e.target.value, 10))}
            className="w-full accent-current"
            style={{ accentColor: "var(--color-accent)" }}
          />
          <span
            className="font-mono text-sm tabular-nums"
            style={{ color: "var(--color-text-muted)" }}
          >
            {months} {t("monthsSuffix")}
          </span>
        </label>

        <label className="flex flex-col gap-3">
          <span className="text-lg font-semibold">{t("team")}</span>
          <input
            type="range"
            min={1}
            max={5}
            value={team}
            onChange={(e) => setTeam(parseInt(e.target.value, 10))}
            className="w-full"
            style={{ accentColor: "var(--color-accent)" }}
          />
          <span
            className="font-mono text-sm tabular-nums"
            style={{ color: "var(--color-text-muted)" }}
          >
            {team} {t("teamSuffix")}
          </span>
        </label>
      </div>

      {/* Stacks + Avoid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="text-lg font-semibold">{t("stacks")}</span>
          <input
            type="text"
            value={stacksInput}
            onChange={(e) => setStacksInput(e.target.value)}
            placeholder={t("stacksPlaceholder")}
            className="rounded-md border px-4 py-3 text-sm"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          />
        </label>
        <label className="flex flex-col gap-2">
          <span className="text-lg font-semibold">{t("avoid")}</span>
          <input
            type="text"
            value={avoidInput}
            onChange={(e) => setAvoidInput(e.target.value)}
            placeholder={t("avoidPlaceholder")}
            className="rounded-md border px-4 py-3 text-sm"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          />
        </label>
      </div>

      {/* Interests — featured */}
      <label className="flex flex-col gap-2">
        <span className="text-lg font-semibold">{t("interests")}</span>
        <textarea
          value={interests}
          onChange={(e) => setInterests(e.target.value)}
          placeholder={t("interestsPlaceholder")}
          rows={4}
          maxLength={500}
          className="resize-none rounded-md border px-4 py-3 text-base leading-relaxed"
          style={{
            background: "var(--color-surface)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        />
        <span
          className="self-end font-mono text-xs"
          style={{ color: "var(--color-text-muted)" }}
        >
          {interests.length}/500
        </span>
      </label>

      {err ? (
        <p
          className="rounded-md border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--color-signal-warn)",
            color: "var(--color-signal-warn)",
            background:
              "color-mix(in srgb, var(--color-signal-warn) 10%, transparent)",
          }}
          role="alert"
        >
          {err}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center gap-3 rounded-full px-7 py-4 text-sm font-semibold shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-60 hover:translate-y-[-1px]"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-elevated)",
            boxShadow:
              "0 16px 32px -14px color-mix(in srgb, var(--color-accent) 55%, transparent)",
          }}
        >
          {busy ? t("submitting") : t("submit")}
          <span aria-hidden>{locale === "ar" ? "←" : "→"}</span>
        </button>
      </div>
    </form>
  );
}
