"use client";

import { useQuery } from "@tanstack/react-query";
import { BlockSkeleton } from "@/components/chat/Skeletons";
import { VerseCard } from "@/components/chat/VerseCard";
import { VersePopup } from "@/components/chat/VersePopup";
import { api } from "@/services/api";

export function AboutDemo() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["demo", "Fp 4:6"], queryFn: () => api.passage("Fp 4:6", "vfl", 0) });
  return (
    <div className="mt-4">
      {isLoading && <BlockSkeleton lines={3} />}
      {isError && <p className="text-vinho">A API não respondeu. Rode scripts/api.sh e recarregue.</p>}
      {data && <VerseCard passage={data} />}
      <VersePopup />
    </div>
  );
}
