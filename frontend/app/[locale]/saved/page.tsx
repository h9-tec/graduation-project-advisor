import { SavedView } from "@/components/saved-view";

export default async function SavedPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return <SavedView locale={locale} />;
}
