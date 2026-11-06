import Link from "next/link";

export function PageFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <Link href="/" className="text-sm font-bold text-couro underline decoration-ouro underline-offset-4">
        Voltar para a conversa
      </Link>
      <h1 className="mt-4 font-escritura text-3xl font-bold text-couro">{title}</h1>
      {children}
    </main>
  );
}
