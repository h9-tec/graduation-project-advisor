import { BlueprintView } from "@/components/blueprint-view";

export default async function BlueprintPage({
  params,
}: {
  params: Promise<{ locale: string; sid: string; cardId: string }>;
}) {
  const { locale, sid, cardId } = await params;
  return <BlueprintView locale={locale} sessionId={sid} cardId={cardId} />;
}
