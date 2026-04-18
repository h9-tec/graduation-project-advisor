import Link from "next/link";
import { useTranslations } from "next-intl";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return <HomeView locale={locale} />;
}

export function HomeView({ locale }: { locale: string }) {
  const t = useTranslations("landing");

  return (
    <section className="relative">
      {/* Diagonal gold rule anchor, faintly behind the content */}
      <div
        aria-hidden
        className="diagonal-rule pointer-events-none absolute inset-0 opacity-40 blur-[0.5px]"
      />
      <div className="relative grid grid-cols-1 gap-10 md:grid-cols-12 md:gap-16">
        <div className="md:col-span-8 fade-rise">
          <p
            className="mb-6 font-mono text-xs uppercase tracking-[0.3em]"
            style={{ color: "var(--color-accent-strong)" }}
          >
            {t("eyebrow")}
          </p>
          <h1
            className="text-5xl leading-[1.05] md:text-7xl lg:text-8xl"
            style={{ fontWeight: 800 }}
          >
            {t("headline")}
          </h1>
          <p
            className="mt-6 max-w-xl text-lg md:text-xl"
            style={{ color: "var(--color-text-muted)" }}
          >
            {t("subhead")}
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href={`/${locale}/onboard`}
              className="group inline-flex items-center gap-3 rounded-full px-7 py-4 text-sm font-semibold shadow-lg transition-all hover:translate-y-[-1px] hover:shadow-xl"
              style={{
                background: "var(--color-accent)",
                color: "var(--color-elevated)",
                boxShadow:
                  "0 16px 32px -14px color-mix(in srgb, var(--color-accent) 55%, transparent)",
              }}
            >
              <span>{t("cta")}</span>
              <span
                aria-hidden
                className="transition-transform group-hover:translate-x-1"
                style={{ display: "inline-block" }}
              >
                {locale === "ar" ? "←" : "→"}
              </span>
            </Link>
          </div>
        </div>

        <aside
          className="md:col-span-4 md:pt-24 fade-rise"
          style={{ animationDelay: "120ms" }}
        >
          <ul
            className="space-y-5 border-s ps-6 font-mono text-xs uppercase tracking-widest"
            style={{
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-muted)",
            }}
          >
            <li>
              <span
                className="me-2 inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: "var(--color-signal-paper)" }}
                aria-hidden
              />
              {t("stats.papers")}
            </li>
            <li>
              <span
                className="me-2 inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: "var(--color-signal-code)" }}
                aria-hidden
              />
              {t("stats.repos")}
            </li>
            <li>
              <span
                className="me-2 inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: "var(--color-accent)" }}
                aria-hidden
              />
              {t("stats.languages")}
            </li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
