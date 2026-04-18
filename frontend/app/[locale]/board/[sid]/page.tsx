import { BoardView } from "@/components/board-view";

export default async function BoardPage({
  params,
}: {
  params: Promise<{ locale: string; sid: string }>;
}) {
  const { locale, sid } = await params;
  return <BoardView locale={locale} sessionId={sid} />;
}
