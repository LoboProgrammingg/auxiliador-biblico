import { AboutDemo } from "@/components/pages/AboutDemo";
import { PageFrame } from "@/components/pages/PageFrame";

const SOURCES = [
  {
    name: "Traduções em português (VFL, NVT, ACF, ARA, NAA e outras)",
    origin: "thiagobodruk/bible",
    license: "Textos com direitos das respectivas editoras; baixados no seu computador para uso pessoal, nunca redistribuídos.",
  },
  {
    name: "Hebraico, aramaico e grego palavra por palavra, léxicos",
    origin: "STEPBible.org — Tyndale House Cambridge",
    license: "CC BY 4.0",
  },
  { name: "Referências cruzadas", origin: "OpenBible.info", license: "CC BY" },
];

export default function Sobre() {
  return (
    <PageFrame title="Sobre">
      <section className="mt-4 max-w-[65ch] space-y-3 leading-relaxed">
        <p>
          O Auxiliador Bíblico é um companheiro de fé, estudo e oração. Ele conversa com você em momentos de aperto,
          depois de uma queda ou quando você quer estudar um tema, e lembra das suas conversas.
        </p>
        <h2 className="pt-3 font-escritura text-xl font-bold text-couro">Como ele evita inventar a Bíblia</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>O modelo não escreve versículos: ele aponta a referência e o texto vem do banco, palavra por palavra.</li>
          <li>Toda referência é conferida antes de aparecer. Se não existir, você vê um aviso no lugar.</li>
          <li>Citações entre aspas e interpretações que contradizem o versículo são sinalizadas automaticamente.</li>
          <li>Você sempre pode clicar na referência para ler o contexto, outras traduções e o texto original.</li>
        </ul>
        <h2 className="pt-3 font-escritura text-xl font-bold text-couro">Experimente</h2>
        <p>Clique na referência abaixo para abrir o versículo com contexto, original e passagens ligadas.</p>
      </section>
      <AboutDemo />
      <section className="mt-8">
        <h2 className="font-escritura text-xl font-bold text-couro">Fontes e licenças</h2>
        <table className="mt-3 w-full text-left text-sm">
          <thead>
            <tr className="border-b border-borda">
              <th className="py-2 pr-3">Conteúdo</th>
              <th className="py-2 pr-3">Origem</th>
              <th className="py-2">Licença</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map((s) => (
              <tr key={s.name} className="border-b border-borda/60 align-top">
                <td className="py-2 pr-3">{s.name}</td>
                <td className="py-2 pr-3">{s.origin}</td>
                <td className="py-2">{s.license}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-4 text-sm text-tinta-suave">
          Em caso de pensamentos de se ferir, ligue para o CVV no 188 (gratuito, 24 horas) ou acesse cvv.org.br.
        </p>
      </section>
    </PageFrame>
  );
}
