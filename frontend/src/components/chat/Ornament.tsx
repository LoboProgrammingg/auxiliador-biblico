export function Divider({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 240 16" className={`h-4 w-60 text-ouro ${className}`} aria-hidden>
      <line x1="0" y1="8" x2="100" y2="8" stroke="currentColor" strokeWidth="0.8" />
      <path d="M120 2 L126 8 L120 14 L114 8 Z" fill="none" stroke="currentColor" strokeWidth="1" />
      <circle cx="120" cy="8" r="1.6" fill="currentColor" />
      <line x1="140" y1="8" x2="240" y2="8" stroke="currentColor" strokeWidth="0.8" />
    </svg>
  );
}

export function Emblem({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={`h-7 w-7 ${className}`} aria-hidden>
      <circle cx="16" cy="16" r="14.5" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.7" />
      <path d="M16 6 V26 M9.5 12.5 H22.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
