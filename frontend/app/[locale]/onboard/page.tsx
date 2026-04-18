import { OnboardForm } from "@/components/onboard-form";
import type { Locale } from "@/i18n";

export default async function OnboardPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return <OnboardForm locale={locale as Locale} />;
}
