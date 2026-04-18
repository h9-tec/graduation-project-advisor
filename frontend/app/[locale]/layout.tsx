import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AtmosphericBg } from "@/components/atmospheric-bg";
import { locales, type Locale } from "@/i18n";
import { fraunces, dmSans, lemonada, jetbrainsMono } from "@/lib/fonts";

import "../globals.css";

export const metadata: Metadata = {
  title: "Graduation Project Advisor",
  description: "Find your graduation project — grounded in papers and code.",
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!locales.includes(locale as Locale)) {
    notFound();
  }
  setRequestLocale(locale);
  const messages = await getMessages();

  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html
      lang={locale}
      dir={dir}
      className={`${fraunces.variable} ${dmSans.variable} ${lemonada.variable} ${jetbrainsMono.variable}`}
    >
      <body suppressHydrationWarning>
        <AtmosphericBg />
        <NextIntlClientProvider messages={messages}>
          <main className="relative mx-auto max-w-6xl px-6 py-16">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
