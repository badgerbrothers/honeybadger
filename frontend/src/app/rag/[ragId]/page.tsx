import { RagDetailPage } from "@/features/rag/RagDetailPage";

export default function RagByIdPage({ params }: { params: { ragId: string } }) {
  return <RagDetailPage ragId={params.ragId} />;
}

