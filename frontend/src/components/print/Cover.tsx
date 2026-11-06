export function Cover({ eyebrow, title, subtitle, date }: { eyebrow: string; title: string; subtitle?: string; date: string }) {
  return (
    <section className="capa">
      <svg className="capa-moldura" viewBox="0 0 210 297" preserveAspectRatio="none" aria-hidden>
        <rect x="12" y="12" width="186" height="273" fill="none" stroke="#a0802f" strokeWidth="0.6" />
        <rect x="15" y="15" width="180" height="267" fill="none" stroke="#a0802f" strokeWidth="0.25" />
        {[[12, 12], [198, 12], [12, 285], [198, 285]].map(([x, y]) => (
          <path key={`${x}-${y}`} d={`M ${x - 3} ${y} L ${x} ${y - 3} L ${x + 3} ${y} L ${x} ${y + 3} Z`} fill="#a0802f" />
        ))}
      </svg>
      <div className="capa-miolo">
        <p className="capa-sobre">{eyebrow}</p>
        <svg viewBox="0 0 64 64" className="capa-emblema" aria-hidden>
          <circle cx="32" cy="32" r="29" fill="none" stroke="#a0802f" strokeWidth="1.2" />
          <path d="M32 12 V52 M20 24 H44" stroke="#4a3524" strokeWidth="3" strokeLinecap="round" />
          <path d="M14 46 Q32 38 50 46" fill="none" stroke="#a0802f" strokeWidth="1.2" />
        </svg>
        <h1 className="capa-titulo">{title}</h1>
        {subtitle && <p className="capa-subtitulo">{subtitle}</p>}
        <svg viewBox="0 0 240 16" className="capa-divisor" aria-hidden>
          <line x1="0" y1="8" x2="100" y2="8" stroke="#a0802f" strokeWidth="0.8" />
          <path d="M120 2 L126 8 L120 14 L114 8 Z" fill="none" stroke="#a0802f" strokeWidth="1" />
          <line x1="140" y1="8" x2="240" y2="8" stroke="#a0802f" strokeWidth="0.8" />
        </svg>
        <p className="capa-data">{date}</p>
      </div>
      <p className="capa-rodape">Auxiliador Bíblico · os versículos vêm do banco local, conferidos palavra por palavra</p>
    </section>
  );
}
