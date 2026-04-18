import { useTranslations } from "next-intl";

export default function HomePage() {
  const t = useTranslations("landing");

  return (
    <section className="flex flex-col gap-6">
      <h1
        className="text-5xl md:text-7xl"
        style={{ fontFamily: "var(--font-display-latin), var(--font-display-arabic)", fontWeight: 800 }}
      >
        {t("headline")}
      </h1>
      <p className="max-w-xl text-lg opacity-80">{t("subhead")}</p>
      <div>
        <button
          type="button"
          className="rounded-md px-5 py-3 text-sm font-medium"
          style={{ background: "var(--color-accent)", color: "var(--color-elevated)" }}
        >
          {t("cta")}
        </button>
      </div>
    </section>
  );
}
