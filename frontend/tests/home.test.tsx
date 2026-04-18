import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ar from "../messages/ar.json";
import HomePage from "../app/[locale]/page";

function renderWithLocale(locale: "en" | "ar") {
  const messages = locale === "en" ? en : ar;
  return render(
    <NextIntlClientProvider messages={messages} locale={locale}>
      <HomePage />
    </NextIntlClientProvider>,
  );
}

describe("HomePage", () => {
  it("renders English headline", () => {
    renderWithLocale("en");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/graduation/i);
  });

  it("renders Arabic headline", () => {
    renderWithLocale("ar");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("تخرج");
  });

  it("renders CTA button in both locales", () => {
    const { unmount } = renderWithLocale("en");
    expect(screen.getByRole("button").textContent).toBe("Start now");
    unmount();
    renderWithLocale("ar");
    expect(screen.getByRole("button").textContent).toBe("ابدأ الآن");
  });
});
