import { GenealogyDiagram } from "@/components/illustrations/GenealogyDiagram";
import { PlacesDiagram } from "@/components/illustrations/PlacesDiagram";
import type { GenealogyLink, GenealogyPerson } from "@/lib/print";
import { fetchApi, query } from "@/lib/server-api";

interface Genealogy {
  reference: string;
  people: GenealogyPerson[];
  links: GenealogyLink[];
}

interface Route {
  reference: string;
  stops: { name: string; lon: number; lat: number; first: string }[];
}

async function Chapter({ reference }: { reference: string }) {
  const [tree, route] = await Promise.all([
    fetchApi<Genealogy>(`/bible/genealogy?${query({ ref: reference })}`),
    fetchApi<Route>(`/bible/route?${query({ ref: reference })}`),
  ]);
  if (!tree && !route) return null;
  const english = tree?.people.some((p) => !p.name_is_pt);
  return (
    <section className="pessoas-lugares">
      <h3>{reference}</h3>
      {tree && (
        <figure className="ilustracao">
          <figcaption>Quem é quem: famílias citadas em {reference}</figcaption>
          <GenealogyDiagram people={tree.people} links={tree.links} />
          <p className="legenda">
            Escuras: pessoas citadas no capítulo; claras: pais, filhos ou cônjuges citados em outras partes da Bíblia. Linha
            tracejada: casamento.{english ? " Nomes com * estão em inglês, como na fonte." : ""} Dados: STEPBible TIPNR, CC BY 4.0.
          </p>
        </figure>
      )}
      {route && (
        <figure className="ilustracao">
          <figcaption>Lugares na ordem em que o texto os menciona</figcaption>
          <PlacesDiagram places={route.stops} route label={`Rota de ${reference}`} />
          <p className="legenda">
            {route.stops.map((s, i) => `${i + 1}. ${s.name} (${s.first})`).join(" → ")}. A ordem é a da narrativa, não um
            trajeto histórico reconstruído. Posições aproximadas: OpenBible.info, CC BY 4.0.
          </p>
        </figure>
      )}
    </section>
  );
}

export async function PeoplePlaces({ chapters }: { chapters: string[] }) {
  if (chapters.length === 0) return null;
  const rendered = await Promise.all(chapters.map((c) => Chapter({ reference: c })));
  if (rendered.every((r) => r === null)) return null;
  return (
    <section className="secao" id="pessoas-lugares">
      <h2>Pessoas e lugares</h2>
      {rendered.map((node, i) => <div key={chapters[i]}>{node}</div>)}
    </section>
  );
}
