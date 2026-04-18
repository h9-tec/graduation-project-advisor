"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark" | "system";

function getSystemPreferredTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const effective = theme === "system" ? getSystemPreferredTheme() : theme;
  document.documentElement.dataset.theme = effective;
}

export function AppHeader({ locale }: { locale: string }) {
  const t = useTranslations("header");
  const router = useRouter();
  const pathname = usePathname();
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    const saved = (localStorage.getItem("theme") as Theme | null) ?? "system";
    setTheme(saved);
    applyTheme(saved);
  }, []);

  const cycleTheme = useCallback(() => {
    const next: Theme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
    setTheme(next);
    localStorage.setItem("theme", next);
    applyTheme(next);
  }, [theme]);

  const switchLocale = useCallback(
    (next: "en" | "ar") => {
      if (!pathname) return;
      const stripped = pathname.replace(/^\/(en|ar)(?=\/|$)/, "") || "/";
      router.push(`/${next}${stripped === "/" ? "" : stripped}`);
    },
    [pathname, router],
  );

  const themeLabel =
    theme === "light" ? "☀︎" : theme === "dark" ? "☾" : "◐";

  return (
    <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 pt-6 text-sm">
      <Link
        href={`/${locale}`}
        className="inline-flex items-center gap-2 font-mono uppercase tracking-[0.2em]"
        style={{ color: "var(--color-text-primary)" }}
      >
        <span
          aria-hidden
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "var(--color-accent)" }}
        />
        <span>Grad · Advisor</span>
      </Link>
      <div className="flex items-center gap-2">
        <div
          className="inline-flex overflow-hidden rounded-full border text-xs"
          style={{ borderColor: "var(--color-border-subtle)" }}
          role="group"
          aria-label={t("language")}
        >
          <button
            type="button"
            onClick={() => switchLocale("en")}
            className="px-3 py-1.5 font-mono uppercase tracking-widest"
            style={{
              background:
                locale === "en" ? "var(--color-accent)" : "transparent",
              color:
                locale === "en"
                  ? "var(--color-elevated)"
                  : "var(--color-text-muted)",
            }}
            aria-pressed={locale === "en"}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => switchLocale("ar")}
            className="px-3 py-1.5 font-mono uppercase tracking-widest"
            style={{
              background:
                locale === "ar" ? "var(--color-accent)" : "transparent",
              color:
                locale === "ar"
                  ? "var(--color-elevated)"
                  : "var(--color-text-muted)",
            }}
            aria-pressed={locale === "ar"}
          >
            AR
          </button>
        </div>
        <button
          type="button"
          onClick={cycleTheme}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border font-mono text-base"
          style={{
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
          aria-label={t("theme")}
          title={`${t("theme")}: ${theme}`}
        >
          {themeLabel}
        </button>
      </div>
    </header>
  );
}
