"use client";

import { useChat } from "@/stores/chat";

export function StatusLine() {
  const status = useChat((s) => s.status);
  if (!status) return null;
  return (
    <p className="pensando flex items-center gap-2 text-sm text-tinta-suave" aria-live="polite">
      <span className="inline-flex gap-1" aria-hidden>
        <span>•</span><span>•</span><span>•</span>
      </span>
      {status}
    </p>
  );
}
