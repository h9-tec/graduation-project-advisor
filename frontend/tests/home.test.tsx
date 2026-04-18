import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ar from "../messages/ar.json";
import { HomeView } from "../app/[locale]/page";

function renderWithLocale(locale: "en" | "ar") {
  const messages = locale === "en" ? en : ar;
  return render(
    <NextIntlClientProvider messages={messages} locale={locale}>
      <HomeView locale={locale} />
    </NextIntlClientProvider>,
  );
}

describe("HomeView", () => {
  it("renders English headline", () => {
    renderWithLocale("en");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/graduation/i);
  });

  it("renders Arabic headline", () => {
    renderWithLocale("ar");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("تخرج");
  });

  it("CTA links to the onboarding route in the current locale", () => {
    const { unmount } = renderWithLocale("en");
    const enLinks = screen.getAllByRole("link");
    const enCta = enLinks.find((l) => l.getAttribute("href") === "/en/onboard");
    expect(enCta).toBeDefined();
    expect(enCta?.textContent).toMatch(/start/i);
    unmount();

    renderWithLocale("ar");
    const arLinks = screen.getAllByRole("link");
    const arCta = arLinks.find((l) => l.getAttribute("href") === "/ar/onboard");
    expect(arCta).toBeDefined();
    expect(arCta?.textContent).toContain("ابدأ");
  });
});
