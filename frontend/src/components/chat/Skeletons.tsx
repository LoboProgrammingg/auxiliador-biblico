export function LineSkeleton({ width = "100%" }: { width?: string }) {
  return <div className="h-3.5 rounded bg-borda/70 motion-safe:animate-pulse" style={{ width }} aria-hidden />;
}

export function BlockSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2.5 py-1" role="status" aria-label="Carregando">
      {Array.from({ length: lines }, (_, i) => (
        <LineSkeleton key={i} width={`${92 - i * 14}%`} />
      ))}
    </div>
  );
}
